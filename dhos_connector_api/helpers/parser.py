from typing import Any, Dict, Optional

from flask import current_app as app
from she_logging import logger

from dhos_connector_api.helpers.converters import parse_sex_to_sct
from dhos_connector_api.helpers.errors import (
    Hl7ApplicationErrorException,
    Hl7ApplicationRejectException,
)
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper

ADT_TYPE_WHITELIST = {
    "A01",  # Admit
    "A02",  # Transfer
    "A03",  # Discharge
    "A04",  # Register a patient
    "A05",  # Pre-admit
    "A08",  # Update patient information
    "A11",  # Cancel admit
    "A12",  # Cancel transfer
    "A13",  # Cancel discharge
    "A14",  # Pending admit
    "A15",  # Pending transfer
    "A21",  # Patient goes on "leave of absence"
    "A22",  # Patient returns from "leave of absence"
    "A23",  # Delete patient record
    "A26",  # Cancel pending transfer
    "A27",  # Cancel pending admit
    "A28",  # Add person information
    "A31",  # Update person information
    "A34",  # Merge patient information - patient ID only
    "A35",  # Merge patient information - account number only
    "A38",  # Cancel pre-admit
    "A40",  # Merge patient - patient identifier list
    "A44",  # Move account information - patient account number
    "A52",  # Cancel patient goes on "leave of absence"
    "A53",  # Cancel patient returns from "leave of absence"
}

ENCOUNTER_TYPE_BLACKLIST = {"WAITLIST", "PREADMIT", "RECURRING"}


def parse_hl7_message(hl7_message: str) -> Hl7Wrapper:
    # Replace CRLF and LF characters with carriage return characters, as
    # otherwise HL7 parsing will fail (expects segments to be delimited
    # only by carriage return characters)
    logger.debug("Parsing HL7 message", extra={"hl7_message": hl7_message})
    hl7_message = hl7_message.replace("\r\n", "\r").replace("\n", "\r")
    try:
        return Hl7Wrapper(hl7_message)
    except AssertionError:
        # Couldn't parse the message, so throw error that will manifest as a 400.
        raise ValueError("Could not parse HL7 message")


def validate_hl7_message(parser: Hl7Wrapper) -> None:
    # Raise application reject if message is not of the expected type.
    logger.debug("Checking message is of the expected type")
    message_category: Optional[str] = parser.get_field_by_hl7_path("MSH.F9.R1.C1")
    if message_category != "ADT":
        raise Hl7ApplicationRejectException(
            f"HL7 message of unexpected type '{message_category}'", parser
        )
    adt_message_type = parser.get_field_by_hl7_path("MSH.F9.R1.C2")
    if adt_message_type not in ADT_TYPE_WHITELIST:
        raise Hl7ApplicationRejectException(
            f"HL7 message of unexpected ADT type '{adt_message_type}'", parser
        )

    # Raise application error if expected segments/fields are missing.
    logger.debug("Checking message has expected segments and fields")
    if not parser.contains_segment("PID"):
        raise Hl7ApplicationErrorException("HL7 PID segment missing", parser)
    if not parser.get_patient_identifier(
        "NHS", default=None
    ) and not parser.get_patient_identifier("MRN", default=None):
        raise Hl7ApplicationRejectException("HL7 MRN and NHS number missing", parser)

    if parser.contains_segment("PV1"):
        encounter_type = parser.get_field_by_hl7_path("PV1.F2")
        if encounter_type in ENCOUNTER_TYPE_BLACKLIST:
            raise Hl7ApplicationErrorException(
                f"HL7 message concerns blacklisted encounter type '{encounter_type}'",
                parser,
            )

        ward_code = parser.get_field_by_hl7_path("PV1.F3.R1.C1")
        if ward_code is None:
            raise Hl7ApplicationErrorException(
                f"HL7 message contains an assigned patient location but the ward code is missing",
                parser,
            )

    # If we got this far, message is valid.
    logger.debug("Message is valid")


def generate_patient_action(m: Hl7Wrapper) -> Dict[str, Any]:
    logger.debug("Generating patient action from ADT message")
    patient_data: dict = {
        "first_name": m.get_field_by_hl7_path("PID.F5.R1.C2"),
        "last_name": m.get_field_by_hl7_path("PID.F5.R1.C1"),
        "sex_sct": parse_sex_to_sct(m.get_field_by_hl7_path("PID.F8")),
    }

    nhs_number = m.get_patient_identifier("NHS", default=None)
    if nhs_number is not None and nhs_number != "":
        patient_data["nhs_number"] = nhs_number

    mrn = m.get_patient_identifier("MRN", default=None)
    if mrn is not None and mrn != "":
        patient_data["mrn"] = mrn

    if m.get_field_by_hl7_path("PID.F7"):
        patient_data["date_of_birth"] = m.get_iso8601_date_by_hl7_path("PID.F7")
    if m.get_field_by_hl7_path("PID.F29"):
        patient_data["date_of_death"] = m.get_iso8601_date_by_hl7_path("PID.F29")

    if "mrn" not in patient_data and "nhs_number" not in patient_data:
        # We have no patient identifiers; raise an application error exception.
        raise Hl7ApplicationErrorException("No patient identifiers in message", m)

    # If message is of type A34 or A40 (patient merge), add previous identifier information.
    # Note: A35 (account number merge) is not included here because we don't currently use
    # account number.
    if m.get_field_by_hl7_path("MSH.F9.R1.C2") in ["A34", "A40"]:

        previous_nhs_number = m.get_merged_patient_identifier("NHS", default=None)
        if previous_nhs_number is not None and previous_nhs_number != "":
            patient_data["previous_nhs_number"] = previous_nhs_number

        previous_mrn = m.get_merged_patient_identifier("MRN", default=None)
        if previous_mrn is not None and previous_mrn != "":
            patient_data["previous_mrn"] = previous_mrn

    patient_action: dict = {"name": "process_patient", "data": patient_data}
    logger.debug("Generated patient action", extra={"patient_action": patient_action})
    return patient_action


def generate_location_action(m: Hl7Wrapper) -> dict:
    logger.debug("Generating location action from ADT message")
    location_data: Dict = {
        "location": {
            "epr_ward_code": m.get_field_by_hl7_path("PV1.F3.R1.C1"),
            "epr_bay_code": m.get_field_by_hl7_path("PV1.F3.R1.C2"),
            "epr_bed_code": m.get_field_by_hl7_path("PV1.F3.R1.C3"),
        }
    }

    # If there is a previous location, add it to the action.
    if m.get_field_by_hl7_path("PV1.F6.R1.C1"):
        location_data["previous_location"] = {
            "epr_ward_code": m.get_field_by_hl7_path("PV1.F6.R1.C1"),
            "epr_bay_code": m.get_field_by_hl7_path("PV1.F6.R1.C2"),
            "epr_bed_code": m.get_field_by_hl7_path("PV1.F6.R1.C3"),
        }

    location_action: Dict = {"name": "process_location", "data": location_data}
    logger.debug(
        "Generated location action", extra={"location_action": location_action}
    )
    return location_action


def generate_encounter_action(m: Hl7Wrapper) -> Dict:
    logger.debug("Generating encounter action from ADT message")
    message_type = m.get_field_by_hl7_path("MSH.F9.R1.C2")
    admission_cancelled: bool = message_type in ["A11", "A23", "A27", "A38"]
    transfer_cancelled: bool = message_type == "A12"
    discharge_cancelled: bool = message_type == "A13"
    encounter_moved: bool = message_type == "A44"
    patient_deceased: bool = m.get_iso8601_date_by_hl7_path("PID.F29") is not None

    encounter_data: Dict = {
        "epr_encounter_id": m.get_field_by_hl7_path("PV1.F19"),
        "location": {
            "epr_ward_code": m.get_field_by_hl7_path("PV1.F3.R1.C1"),
            "epr_bay_code": m.get_field_by_hl7_path("PV1.F3.R1.C2"),
            "epr_bed_code": m.get_field_by_hl7_path("PV1.F3.R1.C3"),
        },
        "encounter_type": m.get_field_by_hl7_path("PV1.F2"),
        "admitted_at": m.get_iso8601_datetime_by_hl7_path(
            "PV1.F44", default_timezone=app.config["SERVER_TIMEZONE"]
        ),
        "admission_cancelled": admission_cancelled,
        "transfer_cancelled": transfer_cancelled,
        "discharge_cancelled": discharge_cancelled,
        "encounter_moved": encounter_moved,
        "patient_deceased": patient_deceased,
    }

    if m.get_field_by_hl7_path("PV1.F45"):
        encounter_data["discharged_at"] = m.get_iso8601_datetime_by_hl7_path(
            "PV1.F45", default_timezone=app.config["SERVER_TIMEZONE"]
        )

    if m.contains_segment("MRG"):
        encounter_data["parent_encounter_id"] = m.get_field_by_hl7_path("MRG.F5.R1.C1")
        encounter_data["epr_previous_location_code"] = m.get_field_by_hl7_path(
            "MRG.F6.R1.C1"
        )

    # If there is a previous location, add it to the action.
    if m.get_field_by_hl7_path("PV1.F6.R1.C1"):
        encounter_data["previous_location"] = {
            "epr_ward_code": m.get_field_by_hl7_path("PV1.F6.R1.C1"),
            "epr_bay_code": m.get_field_by_hl7_path("PV1.F6.R1.C2"),
            "epr_bed_code": m.get_field_by_hl7_path("PV1.F6.R1.C3"),
        }

    encounter_action: Dict = {"name": "process_encounter", "data": encounter_data}
    logger.debug(
        "Generated encounter action", extra={"encounter_action": encounter_action}
    )
    return encounter_action
