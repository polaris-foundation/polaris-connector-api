from pathlib import Path
from typing import Any, Dict

import flask
import pytest
from flask import Flask
from flask.testing import FlaskClient
from mock import Mock
from pytest_mock import MockFixture
from requests import Session
from requests_mock import Mocker
from zeep import Client

from dhos_connector_api.blueprint_api.transmit_controller import (
    CustomTransport,
    create_and_save_cda_message,
    post_hl7_message,
)
from dhos_connector_api.models.hl7_message import Hl7Message


@pytest.fixture
def mock_xsd(requests_mock: Mocker) -> Any:
    xsdfile = Path(__file__).parent / "xmlcda" / "Mirth.xsd"
    return requests_mock.get(
        "http://localhost:8081/services/Mirth?xsd=1", text=xsdfile.read_text()
    )


@pytest.fixture
def mirth_wsdl() -> Path:
    wsdlfile = Path(__file__).parent / "xmlcda" / "ox.wsdl"
    return wsdlfile


@pytest.fixture
def mock_wsdl(requests_mock: Mocker, mock_xsd: Mock, mock_mirth_envs: None) -> Any:
    wsdlfile = Path(__file__).parent / "xmlcda" / "ox.wsdl"
    return requests_mock.get(
        "http://localhost:8081/services/Mirth?wsdl", text=wsdlfile.read_text()
    )


@pytest.fixture
def mock_mirth_post(
    requests_mock: Mocker, mock_wsdl: Path, dummy_soap_response: str
) -> Any:
    headers = {"content_type": "text/xml"}
    endpoint = requests_mock.post(
        "http://localhost:8081/services/Mirth",
        headers=headers,
        text=dummy_soap_response,
    )
    return endpoint


@pytest.fixture
def mock_mirth_post_local(
    requests_mock: Mocker, mock_wsdl: Path, dummy_soap_response: str
) -> Any:
    headers = {"content_type": "text/xml"}
    endpoint = requests_mock.post(
        "http://10.134.180.73:8091/services/Mirth",
        headers=headers,
        text=dummy_soap_response,
    )
    return endpoint


@pytest.fixture
def dummy_soap_response() -> str:
    dummy_response = """
        <?xml version="1.0"?>
        <SOAP-ENV:Envelope
           xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
           SOAP-ENV:encodingStyle="http://www.w3.org/2001/12/soap-encoding">

           <SOAP-ENV:Body xmlns:m="http://ws.connectors.connect.mirth.com/">
             <m:acceptMessageResponse>
                 <m:return>ok</m:return>
             </m:acceptMessageResponse>
           </SOAP-ENV:Body>
        </SOAP-ENV:Envelope>
        """.strip()
    return dummy_response


@pytest.fixture
def mock_mirth_envs(app: Flask) -> None:
    app.config["MIRTH_HOST_URL_BASE"] = "http://localhost:8081/services/Mirth"
    app.config["MIRTH_USERNAME"] = "user1"
    app.config["MIRTH_PASSWORD"] = "password1"


@pytest.fixture
def cdaccd_xml() -> str:
    xmlfile = Path(__file__).parent / "xmlcda" / "cdaccd.xml"
    return xmlfile.read_text()


def test_endpoint(
    requests_mock: Mocker,
    mirth_wsdl: Mock,
    mock_mirth_envs: None,
    mock_mirth_post_local: Mock,
) -> None:
    session = Session()
    client = Client(str(mirth_wsdl), transport=CustomTransport(session=session))
    response = client.service.acceptMessage(arg0="<body>hello world</body>")
    assert response == "ok"


class TestTransmitControllerCDA:
    @pytest.mark.usefixtures("app", "mock_generate_message_control_id")
    def test_save_cda_message(self, cdaccd_xml: str) -> None:
        message_uuid = create_and_save_cda_message(cdaccd_xml)
        msg = Hl7Message.query.filter_by(uuid=message_uuid).first()
        assert msg is not None
        assert msg.dst_description == "mirth"

    def test_post_hl7_message(
        self,
        app: Flask,
        mock_mirth_envs: None,
        cdaccd_xml: str,
        mock_mirth_post_local: Mock,
    ) -> None:
        message_uuid: str = create_and_save_cda_message(cdaccd_xml)
        post_hl7_message(message_uuid)
        assert mock_mirth_post_local.called is True
        assert (
            mock_mirth_post_local.last_request.headers["content-type"]
            == "text/xml; charset=utf-8"
        )
        assert mock_mirth_post_local.last_request.text.startswith("<?xml")
        assert (
            "//server/share/folder/2018L73782250.pdf"
            in mock_mirth_post_local.last_request.text
        )

    @pytest.mark.parametrize(
        "json_body,status_code",
        [
            ({"content": "some xml", "type": "HL7v3CDA"}, 201),
            ({"type": "HL7v3CDA"}, 400),
            ({"content": "some xml", "type": "HL7v2"}, 400),
        ],
    )
    def test_cda_message_route(
        self,
        client: FlaskClient,
        mocker: MockFixture,
        json_body: Dict,
        status_code: int,
        jwt_system: str,
        mock_bearer_authorization: Dict,
    ) -> None:
        from dhos_connector_api.blueprint_api import transmit_controller

        mocker.patch.object(
            transmit_controller,
            "create_and_save_cda_message",
            return_value="9999-9999-9999",
        )
        mocker.patch.object(
            transmit_controller, "post_hl7_message", return_value="9999-9999-9999"
        )

        url = flask.url_for("api.create_cda_message")
        response = client.post(
            url,
            json=json_body,
            headers=mock_bearer_authorization,
        )
        assert response.status_code == status_code
