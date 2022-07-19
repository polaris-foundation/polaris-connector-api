import base64
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Optional
from urllib.parse import ParseResult, urlparse, urlunparse

import requests
from flask import current_app
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from flask_batteries_included.helpers.timestamp import parse_datetime_to_iso8601
from flask_batteries_included.sqldb import db, generate_uuid
from pytz import utc
from requests import Session
from requests.auth import HTTPBasicAuth
from she_logging import logger
from zeep import CachingClient, Transport

from dhos_connector_api.helpers import generator, trustomer
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper
from dhos_connector_api.helpers.jwt import get_epr_service_adapter_headers
from dhos_connector_api.models.hl7_message import Hl7Message


def _base_64_encode(message: str) -> str:
    return base64.b64encode(message.encode("utf8")).decode("utf8")


def create_oru_message(data: Dict) -> None:
    trustomer_config: Dict = trustomer.get_trustomer_config()
    if trustomer_config["send_config"]["generate_oru_messages"] is not True:
        logger.debug("Not sending ORU message due to config")
        return
    db.session.begin(subtransactions=True)
    try:
        oru_message: str = generate_oru_message(raw_data=data)
        hl7_message_uuid: str = create_and_save_hl7_message(hl7_message=oru_message)

        # We track failed requests to TIE by observation_set uuid.
        observation_set_uuid = data["observation_set"]["uuid"]
        post_hl7_message(
            hl7_message_uuid=hl7_message_uuid, observation_set_uuid=observation_set_uuid
        )
        db.session.commit()
    except:
        db.session.rollback()
        raise


def generate_oru_message(raw_data: Dict) -> str:

    # Check required data is present.
    required = ["patient", "encounter", "observation_set"]
    missing_entities = [x for x in required if not raw_data.get(x)]
    if len(missing_entities) > 0:
        raise ValueError(f"Missing data in action: {', '.join(missing_entities)}")
    patient: Dict = raw_data["patient"]
    encounter: Dict = raw_data["encounter"]
    observation_set: Dict = raw_data["observation_set"]

    # Clinician field is optional.
    clinician: Dict = raw_data.get("clinician", None)

    # Generate the ORU message.
    try:
        oru_message: str = generator.generate_oru_message(
            patient, encounter, observation_set, clinician
        )
    except KeyError as e:
        # One of the expected keys in the data was missing.
        raise ValueError(f"Missing key: {e}")

    display_msg: str = oru_message.replace("\r", "\n")
    logger.debug("Generated ORU message", extra={"oru_message": display_msg})

    logger.debug("Transforming outgoing ORU message")
    return _transform_hl7_message(oru_message)


def create_and_save_hl7_message(hl7_message: str) -> str:
    # Save the outgoing message in the database.
    logger.debug("Saving HL7 message in database")
    _hl7_wrapper: Hl7Wrapper = Hl7Wrapper(hl7_message)

    message = Hl7Message()
    message.uuid = generate_uuid()
    message.content = hl7_message
    message.src_description = "dhos"
    message.dst_description = "tie"
    message.is_processed = False
    message.patient_identifiers = _hl7_wrapper.get_patient_identifiers_as_dict()
    message.message_type = _hl7_wrapper.get_message_type_field()
    message.sent_at = _hl7_wrapper.get_message_datetime_iso8601(
        default_timezone=current_app.config["SERVER_TIMEZONE"]
    )
    message.message_control_id = _hl7_wrapper.get_message_control_id()

    db.session.add(message)
    db.session.commit()

    logger.debug("HL7 message saved with UUID %s", message.uuid)
    return message.uuid


def post_hl7_message(
    hl7_message_uuid: str, observation_set_uuid: Optional[str] = None
) -> None:
    logger.debug("POSTing HL7 message to EPR service adapter")
    hl7_message: Hl7Message = Hl7Message.query.get(hl7_message_uuid)

    # The same HL7Message database table is used for both HL7v2 messages destined for TIE fighter
    # and HL7v3 XML messages sent to Mirth. If it's a Mirth message we handle it separately.
    if hl7_message.dst_description == "mirth":
        return post_cda_message(hl7_message)

    url = f"{current_app.config['EPR_SERVICE_ADAPTER_URL_BASE']}/epr/v1/hl7_message"
    headers = get_epr_service_adapter_headers()
    json = {"type": "hl7v2", "body": _base_64_encode(hl7_message.content)}
    message_uuid = hl7_message.uuid
    logger.info("Sending message '%s'", hl7_message.message_control_id)
    _do_send_hl7_message(url=url, headers=headers, json=json, message_uuid=message_uuid)


def _do_send_hl7_message(
    url: str, headers: Dict[str, Any], json: Dict[str, Any], message_uuid: str
) -> None:
    logger.info("Sending HL7 message: %s", message_uuid)
    try:
        post_response = requests.post(url, headers=headers, json=json, timeout=15)
        post_response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.exception(
            "Couldn't send HL7 message %s - received HTTP error %d",
            message_uuid,
            e.response.status_code,
        )
        raise ValueError(e)
    except requests.exceptions.RequestException as e:
        logger.exception(
            "Couldn't send HL7 message %s - connection error", message_uuid
        )
        raise ServiceUnavailableException(e)

    ack_resp = post_response.json()
    ack_resp_body = ack_resp.get("body")

    if not ack_resp_body:
        raise ValueError(
            f"ACK response message expected from EPR, none received for '{message_uuid}'"
        )

    hl7_message: Hl7Message = Hl7Message.query.get(message_uuid)
    ack_msg: str = base64.b64decode(ack_resp_body).decode("utf8")
    hl7_message.ack = ack_msg
    ack_msg = ack_msg.replace("\r\n", "\r").replace("\n", "\r")
    hl7_parsed: Hl7Wrapper = Hl7Wrapper(ack_msg)

    ack_field = hl7_parsed.get_field_by_hl7_path("MSA.F1")

    if ack_field == "AA":
        logger.info(
            "Message '%s' has been successfully received",
            hl7_message.message_control_id,
        )
    else:
        logger.error(
            "Message '%s' did not receive a successful acknowledgement. (%s)",
            hl7_message.message_control_id,
            ack_field,
        )

    hl7_message.is_processed = True
    db.session.commit()


def _transform_hl7_message(raw_message: str) -> str:
    # Attempt to use provided HL7 message converter
    module_name: str = current_app.config["HL7_TRANSFORMER_MODULE"]
    logger.debug("Transforming using module '%s'", module_name)
    try:
        converter: Any = import_module(module_name)
        return converter.transform_outgoing(raw_message)
    except (ImportError, AttributeError):
        raise ServiceUnavailableException("HL7 message converter is unavailable")


def create_and_save_cda_message(cda_message: str) -> str:
    # Save the outgoing message in the database.
    logger.debug("Saving HL7 CDA message in database")
    message = Hl7Message()
    message.uuid = generate_uuid()
    message.content = cda_message
    message.src_description = "dhos"
    message.dst_description = "mirth"
    message.is_processed = False
    message.patient_identifiers = None
    message.message_type = None
    message.sent_at = parse_datetime_to_iso8601(datetime.now(tz=utc))
    message.message_control_id = None

    db.session.add(message)
    db.session.commit()

    logger.debug("HL7 CDA message saved with UUID %s", message.uuid)
    return message.uuid


def post_cda_message(hl7_message: Hl7Message) -> None:
    logger.debug("POSTing CDA message to Mirth")
    body = hl7_message.content

    if not current_app.config["MIRTH_HOST_URL_BASE"]:
        logger.warning("Post CDA message called, Mirth host not configured")
        return

    _do_send_cda_message(body)

    hl7_message.is_processed = True
    db.session.commit()

    logger.debug("Processed and sent CDA message")


def _do_send_cda_message(body: str) -> None:
    url = f"{current_app.config['MIRTH_HOST_URL_BASE']}?wsdl"
    session = Session()
    session.auth = HTTPBasicAuth(
        current_app.config["MIRTH_USERNAME"], current_app.config["MIRTH_PASSWORD"]
    )
    client: CachingClient = CachingClient(
        url, transport=CustomTransport(session=session)
    )
    response = client.service.acceptMessage(arg0=body)
    logger.debug("CDA response: %s", response)


class CustomTransport(Transport):
    def load(self, url: str) -> bytes:
        """
        Allow the SOAP XML configured service endpoint to be replaced with the MIRTH_HOST_URL_BASE.
        This is required in order to translate the returned local address inside the XML to a valid network address.
        """
        override_url: ParseResult = urlparse(current_app.config["MIRTH_HOST_URL_BASE"])
        origin_url: ParseResult = urlparse(url)
        if origin_url.scheme in ("http", "https"):
            url = urlunparse(
                (
                    override_url.scheme,
                    override_url.netloc,
                    origin_url.path,
                    origin_url.params,
                    origin_url.query,
                    origin_url.fragment,
                )
            )

        return super(CustomTransport, self).load(url)
