import base64
from typing import Any, Dict

import pytest
import requests
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from pytest_mock import MockFixture
from requests_mock import Mocker

from dhos_connector_api.blueprint_api import receive_controller, transmit_controller
from dhos_connector_api.blueprint_api.transmit_controller import (
    create_and_save_hl7_message,
    generate_oru_message,
    post_hl7_message,
)
from dhos_connector_api.helpers import generator
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper
from dhos_connector_api.models.hl7_message import Hl7Message


@pytest.mark.usefixtures("app")
class TestTransmitController:
    def test_generate_oru_message_success(
        self, mocker: MockFixture, process_obs_set_message_body: Dict, oru_message: str
    ) -> None:
        mock_create = mocker.patch.object(generator, "generate_oru_message")
        mock_create.return_value = oru_message
        data = process_obs_set_message_body["actions"][0]["data"]
        generate_oru_message(data)
        mock_create.assert_called_once_with(
            data["patient"],
            data["encounter"],
            data["observation_set"],
            data["clinician"],
        )

    def test_generate_oru_message_data_missing(
        self, process_obs_set_message_body: Dict
    ) -> None:
        data = process_obs_set_message_body["actions"][0]["data"]
        del data["patient"]
        with pytest.raises(ValueError):
            generate_oru_message(data)

    def test_generate_oru_message_data_garbage(
        self, process_obs_set_message_body: Dict
    ) -> None:
        data = process_obs_set_message_body["actions"][0]["data"]
        data["patient"] = {"key": "value"}
        data["clinician"] = {"key": "value"}
        data["encounter"] = {"key": "value"}
        data["observation_set"] = {"key": "value"}
        with pytest.raises(ValueError):
            generate_oru_message(data)

    @pytest.mark.usefixtures("mock_generate_message_control_id")
    def test_save_oru_message(self, oru_message: str) -> None:
        create_and_save_hl7_message(oru_message)
        expected_message_control_id = Hl7Wrapper.generate_message_control_id()
        msg = Hl7Message.query.filter_by(
            message_control_id=expected_message_control_id
        ).first()
        assert msg is not None
        assert msg.message_type == "ORU^R01^ORU_R01"

    def test_post_hl7_message_receive_ack(
        self, mocker: MockFixture, oru_message: str, requests_mock: Mocker, caplog: Any
    ) -> None:
        mock_headers = {"some": "auth"}
        mocker.patch.object(
            transmit_controller,
            "get_epr_service_adapter_headers",
            return_value=mock_headers,
        )
        response = {
            "type": "hl7v2",
            "body": "TVNIfF5+XFwmfE9YT05fVElFX0FEVHxPWE9OfGMwNDgxfE9YT058MjAxOTA3MDIxNzEzMDF8fEFDS15BMDF8OTE4MzE3MTMwMTUxNDIzMEo0WVB8UHwyLjMNCk1TQXxBQXxURVNUTVNHMzMzMw==",
        }
        mock_post: Any = requests_mock.post(
            f"http://epr-service-adapter/epr/v1/hl7_message", json=response
        )

        message_uuid: str = create_and_save_hl7_message(oru_message)
        post_hl7_message(message_uuid, "123-456")
        assert mock_post.called is True

        encoded_oru_message: str = base64.b64encode(
            oru_message.encode(encoding="utf8")
        ).decode("utf8")

        assert mock_post.last_request.headers["some"] == "auth"
        assert mock_post.last_request.json() == {
            "type": "hl7v2",
            "body": encoded_oru_message,
        }
        hl7_msg = Hl7Message.query.get(message_uuid)
        assert hl7_msg.ack == base64.b64decode(response["body"]).decode("utf8")

        assert any(
            m.endswith(f"Message '224ddf783bc4cc6c158f' has been successfully received")
            for m in caplog.messages
        )

    def test_post_hl7_message_receive_nack(
        self, mocker: MockFixture, oru_message: str, requests_mock: Mocker, caplog: Any
    ) -> None:
        mock_headers = {"some": "auth"}
        mocker.patch.object(
            transmit_controller,
            "get_epr_service_adapter_headers",
            return_value=mock_headers,
        )
        response = {
            "type": "hl7v2",
            "body": "TVNIfF5+XFwmfE9YT05fVElFX0FEVHxPWE9OfGMwNDgxfE9YT058MjAxOTA3MDIxNzEzMDF8fEFDS15BMDF8OTE4MzE3MTMwMTUxNDIzMEo0WVB8UHwyLjMNCk1TQXxBUnxURVNUTVNHMzMzMw==",
        }
        mock_post: Any = requests_mock.post(
            f"http://epr-service-adapter/epr/v1/hl7_message", json=response
        )

        message_uuid: str = create_and_save_hl7_message(oru_message)
        post_hl7_message(message_uuid, "123-456")
        assert mock_post.called is True

        encoded_oru_message: str = base64.b64encode(
            oru_message.encode(encoding="utf8")
        ).decode("utf8")

        assert mock_post.last_request.headers["some"] == "auth"
        assert mock_post.last_request.json() == {
            "type": "hl7v2",
            "body": encoded_oru_message,
        }

        hl7_msg = Hl7Message.query.get(message_uuid)
        assert hl7_msg.ack == base64.b64decode(response["body"]).decode("utf8")

        assert any(
            m.endswith(
                f"Message '224ddf783bc4cc6c158f' did not receive a successful acknowledgement. (AR)"
            )
            for m in caplog.messages
        )

    def test_post_hl7_message_exception_handling_timeout(
        self, requests_mock: Mocker, oru_message: str, mocker: MockFixture
    ) -> None:
        mock_post: Any = requests_mock.post(
            f"http://epr-service-adapter/epr/v1/hl7_message",
            exc=requests.exceptions.Timeout,
        )
        mocker.patch.object(
            transmit_controller,
            "get_epr_service_adapter_headers",
            return_value={"some": "auth"},
        )
        message_uuid: str = create_and_save_hl7_message(oru_message)
        with pytest.raises(ServiceUnavailableException):
            post_hl7_message(message_uuid, "123-456")
        assert mock_post.call_count == 1
        existing_message = receive_controller.get_hl7_message(message_uuid)
        assert existing_message["uuid"] == message_uuid
        assert existing_message["is_processed"] is False

    def test_post_hl7_message_exception_handling_http_error(
        self, requests_mock: Mocker, oru_message: str, mocker: MockFixture
    ) -> None:
        mock_post: Any = requests_mock.post(
            f"http://epr-service-adapter/epr/v1/hl7_message", status_code=400
        )
        mocker.patch.object(
            transmit_controller,
            "get_epr_service_adapter_headers",
            return_value={"some": "auth"},
        )
        message_uuid: str = create_and_save_hl7_message(oru_message)
        with pytest.raises(ValueError):
            post_hl7_message(message_uuid, "123-456")
        assert mock_post.call_count == 1
        existing_message = receive_controller.get_hl7_message(message_uuid)
        assert existing_message["uuid"] == message_uuid
        assert existing_message["is_processed"] is False
