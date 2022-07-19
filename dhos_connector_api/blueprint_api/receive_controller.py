import base64
import binascii
import sqlite3
from importlib import import_module
from typing import Any, Dict, List, Optional

import kombu_batteries_included
from flask import current_app
from flask_batteries_included.sqldb import db, generate_uuid
from she_logging import logger
from sqlalchemy import cast
from sqlalchemy.exc import IntegrityError

from dhos_connector_api.helpers.errors import (
    Hl7ApplicationErrorException,
    Hl7ApplicationRejectException,
)
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper
from dhos_connector_api.helpers.parser import (
    generate_encounter_action,
    generate_location_action,
    generate_patient_action,
    parse_hl7_message,
    validate_hl7_message,
)
from dhos_connector_api.models.hl7_message import Hl7Message


def create_and_process_hl7_message(body_b64: str) -> Dict:
    logger.info("Received base64 encoded HL7 message")
    message = Hl7Message()
    message.uuid = generate_uuid()
    message.content = body_b64  # Save the base64 encoded content initially
    message.src_description = "tie"
    message.dst_description = "dhos"
    message.is_processed = False
    db.session.add(message)

    # Try to parse the message. If parsing fails, write what we can do the database so we can investigate
    # the error - we don't respond with a (N)ACK as we can't even parse the message (so can't refer to
    # it in the (N)ACK).
    # 1) Decode the content and overwrite the model field.
    # 2) Transform the message with any trust-specific logic.
    # 3) Parse the message into HL7 wrapper structure
    try:
        message.content = _decode_b64_message(body_b64)
        logger.debug("Decoded HL7 message", extra={"hl7_message": message.content})
        message.content = _transform_hl7_message(message.content)
        logger.debug("Transformed incoming HL7 message")
        hl7_wrapper: Hl7Wrapper = parse_hl7_message(message.content)
        logger.debug("Parsed HL7 message")
    except ValueError as e:
        logger.error("Failed to parse incoming HL7 message: %s", str(e))
        db.session.commit()
        raise

    # Try to validate the message. If validation fails, handle the resulting exception and generate
    # a (N)ACK.
    processed_message: Optional[Dict] = None
    is_message_valid = True
    try:
        validate_hl7_message(hl7_wrapper)
        logger.debug("Validated HL7 message")
        message.patient_identifiers = hl7_wrapper.get_patient_identifiers_as_dict()
        message.message_type = hl7_wrapper.get_message_type_field()
        message.sent_at = hl7_wrapper.get_message_datetime_iso8601(
            default_timezone=current_app.config["SERVER_TIMEZONE"]
        )
        message.message_control_id = hl7_wrapper.get_message_control_id()
        message.ack = hl7_wrapper.generate_ack(ack_code="AA")
        logger.info("Received message '%s' for processing", message.message_control_id)
        processed_message = process_hl7_message(message.uuid, hl7_wrapper)
    except Hl7ApplicationRejectException as e:
        # Generate an AR (N)ACK message.
        logger.warning("Failed to process message: %s", e.reason)
        message.ack = e.wrapped_message.generate_ack(
            ack_code="AR",
            error_code=str(Hl7ApplicationRejectException.__name__),
            error_msg=e.reason,
        )
        is_message_valid = False
    except Hl7ApplicationErrorException as e:
        # Generate an AE (N)ACK message.
        logger.warning("Failed to process message: %s", e.reason)
        message.ack = e.wrapped_message.generate_ack(
            ack_code="AE",
            error_code=str(Hl7ApplicationErrorException.__name__),
            error_msg=e.reason,
        )
        is_message_valid = False
    except Exception as e:
        # Generate an AE (N)ACK message. The error was not a custom exception raised by our
        # validation/processing, which means it is an unexpected error that we don't have
        # explicit checks for - worth flagging a bit more loudly than just a warning.
        logger.exception(
            "Failed to process message: unexpected error, check the HL7 message contents"
        )
        message.ack = hl7_wrapper.generate_ack(
            ack_code="AE",
            error_code=str(Hl7ApplicationErrorException.__name__),
            error_msg=f"Unexpected error: {type(e).__name__}",
        )
        is_message_valid = False

    try:
        db.session.commit()
    except IntegrityError as e:
        if "unique constraint" not in str(e).lower():
            # Unexpected error - re-raise.
            raise
        # Message is a duplicate. Generate an AR (N)ACK message. Set the message control ID
        # to None so it can be saved in the database.
        logger.warning("Failed to process message: duplicate message control ID")
        message.ack = hl7_wrapper.generate_ack(
            ack_code="AR",
            error_code=str(Hl7ApplicationRejectException.__name__),
            error_msg="HL7 message appears to be duplicate",
        )
        message.message_control_id = None
        db.session.rollback()
        db.session.add(message)
        db.session.commit()
        is_message_valid = False

    # If validation succeeded, publish the message internally.
    if is_message_valid and processed_message is not None:
        # Publish the message to the rest of the platform.
        logger.debug(
            "Publishing internal message to DHOS",
            extra={"message_body": processed_message},
        )
        # SCTID: 24891000000101 - EDI message (record artifact)
        kombu_batteries_included.publish_message(
            routing_key="dhos.24891000000101", body=processed_message
        )
        logger.debug("Published internal message to DHOS")

    # Encode the resulting (N)ACK HL7 message.
    logger.debug("Responding to HTTP request with ACK: %s", message.ack)
    b64encoded_ack_message = base64.b64encode(message.ack.encode("utf8")).decode("utf8")

    return {
        "uuid": message.uuid,
        "body": b64encoded_ack_message,
        "type": "HL7v2",
    }


def update_hl7_message(message_id: str, _json: dict) -> None:
    logger.info(
        "Updating HL7 message with uuid %s",
        message_id,
        extra={"hl7_message_data": _json},
    )
    device = Hl7Message.query.filter_by(uuid=message_id).first_or_404()
    for key in _json:
        setattr(device, key, _json[key])
    db.session.add(device)
    db.session.commit()


def process_hl7_message(msg_uuid: str, m: Hl7Wrapper) -> Dict:
    actions: List[Dict] = [generate_patient_action(m)]

    # An HL7 message may not have admission date information in the PV1 segment
    # This appears to occur in A08 messages. If the admission date (PV1.F44) is
    # missing do not attempt to update the location and encounter information
    if m.contains_segment("PV1") and m.get_field_by_hl7_path("PV1.F44"):
        actions.append(generate_location_action(m))
        actions.append(generate_encounter_action(m))

    return {"dhos_connector_message_uuid": msg_uuid, "actions": actions}


def _decode_b64_message(b64_message: str) -> str:
    try:
        return base64.b64decode(b64_message).decode("utf8")
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError(f"Message body could not be decoded as base64: {b64_message}")


def _transform_hl7_message(raw_message: str) -> str:
    # Attempt to use provided HL7 message converter
    module_name: str = current_app.config["HL7_TRANSFORMER_MODULE"]
    logger.debug("Transforming using module '%s'", module_name)
    try:
        converter: Any = import_module(module_name)
        return converter.transform_incoming(raw_message)
    except (ImportError, AttributeError):
        raise ValueError("HL7 message converter is unavailable")


def get_hl7_message(message_uuid: str) -> dict:
    message = Hl7Message.query.filter_by(uuid=message_uuid).first_or_404()
    return message.to_dict()


def get_hl7_message_by_message_control_id(message_control_id: str) -> List[dict]:
    messages = Hl7Message.query.filter_by(
        message_control_id=message_control_id
    ).order_by(Hl7Message.created.desc())
    return [message.to_dict() for message in messages]


def get_hl7_message_by_identifier(identifier_type: str, identifier: str) -> List[dict]:
    messages = db.session.query(Hl7Message).filter(
        cast(Hl7Message.patient_identifiers[identifier_type], db.String)
        == '"' + identifier + '"'
    )

    return [message.to_dict() for message in messages]
