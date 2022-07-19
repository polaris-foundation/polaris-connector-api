import base64
from pathlib import Path
from typing import Dict
from unittest.mock import Mock

import kombu_batteries_included
import pytest
from flask_batteries_included.helpers.error_handler import EntityNotFoundException
from pytest_mock import MockFixture
from werkzeug import Client

from dhos_connector_api.blueprint_api import transmit_controller
from dhos_connector_api.helpers import trustomer


@pytest.mark.usefixtures("app")
class TestApi:
    B64_BODY = (
        "TVNIfF5+XFxcJnxjMDQ4MXxPWE9OfE9YT05fVElFX0FEVHxPWE9OfDIwMTcwNzMxMTQxMzQ4fH"
        "xBRFReQTAxfFE1NDkyOTE2ODJUNTUwNDU0MDU5WDE4MzkxQTEwOTZ8UHwyLjN8fHx8fHw4ODU5"
        "LzFcbkVWTnxBMDF8MjAxNzA3MzExNDEzMDB8fHxSQkZUSElSS0VMTFMyXlRoaXJrZWxsXlN0ZX"
        "BoZW5eXl5eXl5cIlwiXlBSU05MXl5eT1JHRFJeXCJcIlxuUElEfDF8MTA1MzIzODBeXl5OT0Mt"
        "TVJOXk1STl5cIlwifDEwNTMyMzgwXl5eTk9DLU1STl5NUk5eXCJcInx8WlpaRURVQ0FUSU9OXl"
        "NURVBIRU5eXl5eXkNVUlJFTlR8fDE5ODIxMTAzfDF8fFwiXCJ8Q2h1cmNoaWxsIEhvc3BpdGFs"
        "Xk9sZCBSb2FkXk9YRk9SRF5cIlwiXk9YMyA3TEVeR0JSXkhPTUVeSGVhZGluZ3Rvbl5cIlwiXl"
        "5eXl5eXl5cIlwifHx8fFwiXCJ8XCJcInxcIlwifDkwNDc4NTQ4OF5eXk5PQy1FbmNudHIgTnVt"
        "YmVyXkZJTk5CUl5cIlwifHx8fEN8fFwiXCJ8fFwiXCJ8XCJcInxcIlwifHxcIlwiXG5QRDF8fH"
        "xKRVJJQ0hPIEhFQUxUSCBDRU5UUkUgKEtFQVJMRVkpXl5LODQwMjZ8Rzg0MDQyMzFeQ0hJVkVS"
        "U15BTkRZXkFCRFVTXl5eXlwiXCJeRVhUSURcblpQSXwxfHx8fHx8fHxcIlwifEc4NDA0MjMxXk"
        "NISVZFUlNeQU5EWV5BQkRVU3x8XCJcInxcIlwifFwiXCJ8XCJcInx8fHx8fHxcIlwiXG5QVjF8"
        "MXxJTlBBVElFTlR8Tk9DLVdhcmQgQl5EYXkgUm9vbV5DaGFpciA2Xk5PQ15eQkVEXk11c2N8Mj"
        "J8fFwiXCJeXCJcIl5cIlwiXlwiXCJeXl5cIlwifEMxNTI0OTcwXkJ1cmdlXlBldGVyXkRlbmlz"
        "Xl5Ncl5eXk5IU0NPTlNVTFROQlJeUFJTTkxeXl5OT05HUF5cIlwifjMzMzc5ODEwMzAzN15CdX"
        "JnZV5QZXRlcl5EZW5pc15eTXJeXl5EUk5CUl5QUlNOTF5eXk9SR0RSXlwiXCJ8dGVzdGNvbnN1"
        "bHRhbnReVGVzdF5UZXN0Xl5eXl5eXCJcIl5QUlNOTF5eXk9SR0RSXlwiXCJ8fDExMHxcIlwifF"
        "wiXCJ8XCJcInwxOXxcIlwifFwiXCJ8fElOUEFUSUVOVHw5MDkxMjc4MDVeXlwiXCJeTk9DLUF0"
        "dGVuZGFuY2VeVklTSVRJRHxcIlwifHxcIlwifHx8fHx8fHx8fHx8fHxcIlwifFwiXCJ8XCJcIn"
        "xOT0N8fEFDVElWRXx8fDIwMTcwNzMxMTQxMzAwXG5QVjJ8fDF8fHx8fFwiXCJ8fDIwMTcwNzMx"
        "MDAwMDAwfHx8fFwiXCJ8fHx8fHx8fFwiXCJ8XCJcInxeXjY0Nzg0Mw=="
    )
    A02_MSG = {
        "dhos_connector_message_uuid": "e17a6f02-7d0e-407e-88dc-237940b05353",
        "actions": [
            {
                "name": "process_patient",
                "data": {
                    "first_name": "STEPHEN",
                    "last_name": "ZZZASSESSMENTS",
                    "sex_sct": "248153007",
                    "mrn": "90462826",
                    "date_of_birth": "1982-11-03",
                },
            },
            {
                "name": "process_location",
                "data": {
                    "location": {
                        "epr_ward_code": "J-WD 5A",
                        "epr_bay_code": "Room 01",
                        "epr_bed_code": "Bed A",
                    },
                    "previous_location": {
                        "epr_ward_code": "J-WD WWRecovery",
                        "epr_bay_code": "In Theatre",
                        "epr_bed_code": "Bed 01",
                    },
                },
            },
            {
                "name": "process_encounter",
                "data": {
                    "epr_encounter_id": "909127805",
                    "location": {
                        "epr_ward_code": "NOC-Ward B",
                        "epr_bay_code": "Day Room",
                        "epr_bed_code": "Chair 6",
                    },
                    "encounter_type": "INPATIENT",
                    "admitted_at": "2017-07-31T14:13:00.000Z",
                    "admission_cancelled": False,
                    "transfer_cancelled": False,
                    "discharge_cancelled": False,
                    "encounter_moved": False,
                    "patient_deceased": False,
                    "previous_location": {
                        "epr_ward_code": "J-WD WWRecovery",
                        "epr_bay_code": "In Theatre",
                        "epr_bed_code": "Bed 01",
                    },
                },
            },
        ],
    }
    A05_MSG = {
        "dhos_connector_message_uuid": "1fda0b1c-6fc7-41f2-83b8-6d5c0a18497b",
        "actions": [
            {
                "name": "process_patient",
                "data": {
                    "first_name": "ELEPHANT",
                    "last_name": "ZZZTEST",
                    "sex_sct": "248152002",
                    "mrn": "90532208",
                    "date_of_birth": "1990-01-01",
                },
            }
        ],
    }

    A38_MSG = {
        "dhos_connector_message_uuid": "88a363c7-2877-4f53-845b-2a063e5762ee",
        "actions": [
            {
                "name": "process_location",
                "data": {
                    "location": {
                        "epr_ward_code": "WBE",
                        "epr_bay_code": "",
                        "epr_bed_code": "",
                    }
                },
            },
            {
                "name": "process_encounter",
                "data": {
                    "epr_encounter_id": "2018L4338243",
                    "location": {
                        "epr_ward_code": "WBE",
                        "epr_bay_code": "",
                        "epr_bed_code": "",
                    },
                    "encounter_type": "DAYCASE",
                    "admitted_at": "2018-01-15T16:30:00.000Z",
                    "admission_cancelled": True,
                    "transfer_cancelled": False,
                    "discharge_cancelled": False,
                    "encounter_moved": False,
                    "patient_deceased": False,
                },
            },
        ],
    }

    @pytest.fixture(autouse=True)
    def mock_publish(self, mocker: MockFixture) -> Mock:
        return mocker.patch.object(kombu_batteries_included, "publish_message")

    def test_post_v1_hl7_success(
        self, client: Client, mock_bearer_authorization: Dict
    ) -> None:

        response = client.post(
            "/dhos/v1/message",
            json={"type": "HL7v2", "body": self.B64_BODY},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 200

    def test_post_hl7_failure_unknown_type(
        self, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        response = client.post(
            "/dhos/v1/message",
            json={"type": "blargh", "body": self.B64_BODY},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 400

    def test_post_hl7_failure_no_request_body(
        self, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        response = client.post(
            "/dhos/v1/message",
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 400

    def test_post_hl7_failure_missing_body_field(
        self, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        response = client.post(
            "/dhos/v1/message",
            json={"type": "HL7v2"},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 400

    def test_patch_hl7_success(
        self, mocker: MockFixture, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        mocker.patch(
            "dhos_connector_api.blueprint_api.receive_controller.update_hl7_message"
        )
        response = client.patch(
            "/dhos/v1/message/someuuid",
            json={"is_processed": True},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 204

    def test_patch_hl7_invalid(
        self, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        response = client.patch(
            "/dhos/v1/message/someuuid",
            json={"blargh": "blerg"},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 400

    def test_patch_hl7_unknown(
        self, mocker: MockFixture, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        mock_create = mocker.patch(
            "dhos_connector_api.blueprint_api.receive_controller.update_hl7_message"
        )
        mock_create.side_effect = EntityNotFoundException()
        response = client.patch(
            "/dhos/v1/message/someuuid",
            json={"is_processed": True},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 404

    # OUH blacklist A05 ('WAITLIST') messages
    def test_from_hl7_a05_failure(
        self, client: Client, mock_bearer_authorization: Dict
    ) -> None:
        file_to_open = Path("tests/samples/A05.hl7")
        with open(file_to_open, "r") as f:
            hl7 = f.read()
        hl7_bytes = base64.b64encode(hl7.encode("utf8"))
        response = client.post(
            "/dhos/v1/message",
            json={"type": "HL7v2", "body": hl7_bytes.decode()},
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 200
        assert response.json is not None
        ack_message_encoded: str = response.json["body"]
        assert isinstance(ack_message_encoded, str)
        ack_message_decoded: str = base64.b64decode(
            ack_message_encoded.encode("utf8")
        ).decode("utf8")
        assert "Hl7ApplicationErrorException" in ack_message_decoded

    @pytest.mark.parametrize(
        "expected_status,request_body",
        [
            (400, {"key": "value"}),
            (400, {"actions": "not a list"}),
            (400, {"actions": [{"not": "a string"}]}),
        ],
    )
    def test_oru_message_invalid(
        self,
        client: Client,
        expected_status: int,
        request_body: Dict,
        mock_bearer_authorization: Dict,
    ) -> None:
        response = client.post(
            "/dhos/v1/oru_message",
            json=request_body,
            headers=mock_bearer_authorization,
        )
        assert response.status_code == expected_status

    @pytest.mark.usefixtures("mock_trustomer_config")
    def test_create_oru_message_calls_post(
        self,
        mocker: MockFixture,
        client: Client,
        process_obs_set_message_body: Dict,
        mock_bearer_authorization: Dict,
    ) -> None:
        mock_post = mocker.patch.object(transmit_controller, "post_hl7_message")
        data = process_obs_set_message_body["actions"][0]["data"]
        payload = {"actions": [{"name": "process_observation_set", "data": data}]}
        client.post(
            "/dhos/v1/oru_message",
            json=payload,
            headers=mock_bearer_authorization,
        )
        assert mock_post.call_count == 1

    def test_oru_message_not_sent_by_config(
        self,
        mocker: MockFixture,
        client: Client,
        process_obs_set_message_body: Dict,
        mock_bearer_authorization: Dict,
    ) -> None:
        data = process_obs_set_message_body["actions"][0]["data"]
        payload = {"actions": [{"name": "process_observation_set", "data": data}]}
        mocker.patch.object(
            trustomer,
            "get_trustomer_config",
            return_value={"send_config": {"generate_oru_messages": False}},
        )
        mock_generate = mocker.patch.object(transmit_controller, "generate_oru_message")
        response = client.post(
            "/dhos/v1/oru_message",
            json=payload,
            headers=mock_bearer_authorization,
        )
        assert response.status_code == 204
        mock_generate.assert_not_called()
