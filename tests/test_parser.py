import pytest

from dhos_connector_api.helpers.errors import (
    Hl7ApplicationErrorException,
    Hl7ApplicationRejectException,
)
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper
from dhos_connector_api.helpers.parser import parse_hl7_message, validate_hl7_message


def test_parse_hl7_message_success(hl7_message: str) -> None:
    wrapped: Hl7Wrapper = parse_hl7_message(hl7_message)
    expected = hl7_message.replace("\r\n", "\r").replace("\n", "\r")
    assert wrapped.raw_message == expected


def test_parse_hl7_message_missing_header(hl7_message: str) -> None:
    hl7 = "".join(
        [line for line in hl7_message.split("\n") if not line.startswith("MSH")]
    )
    with pytest.raises(ValueError):
        parse_hl7_message(hl7)


def test_validate_hl7_message_missing_patient_identifier(hl7_message: str) -> None:
    hl7 = hl7_message.replace("654321^^^NOC-MRN^MRN^", "654321^^^NOC-XXX^XXX^")
    hl7 = hl7.replace("NHSNBR", "XXXXXX")
    hl7 = hl7.replace("NHSNMBR", "XXXXXXX")
    wrapped = parse_hl7_message(hl7)
    with pytest.raises(Hl7ApplicationRejectException):
        validate_hl7_message(wrapped)


def test_validate_hl7_message_location_ward_code(hl7_message: str) -> None:
    hl7 = hl7_message.replace("NOC-Ward B", '""')
    wrapped = parse_hl7_message(hl7)
    with pytest.raises(Hl7ApplicationErrorException):
        validate_hl7_message(wrapped)


def test_validate_hl7_message_not_adt(hl7_message: str) -> None:
    hl7 = hl7_message.replace("ADT^A01", "ZZZ^ZZZ")
    wrapped = parse_hl7_message(hl7)
    with pytest.raises(Hl7ApplicationRejectException):
        validate_hl7_message(wrapped)


def test_validate_hl7_message_unknown_adt_type(hl7_message: str) -> None:
    hl7 = hl7_message.replace("ADT^A01", "ADT^B99")
    wrapped = parse_hl7_message(hl7)
    with pytest.raises(Hl7ApplicationRejectException):
        validate_hl7_message(wrapped)


def test_validate_hl7_message_missing_pid(hl7_message: str) -> None:
    hl7 = "".join(
        [line for line in hl7_message.split("\n") if not line.startswith("PID")]
    )
    wrapped = parse_hl7_message(hl7)
    with pytest.raises(Hl7ApplicationErrorException):
        validate_hl7_message(wrapped)


def test_validate_hl7_message_unexpected_encounter_type(hl7_message: str) -> None:
    hl7 = hl7_message.replace("INPATIENT", "WAITLIST")
    wrapped = parse_hl7_message(hl7)
    with pytest.raises(Hl7ApplicationErrorException):
        validate_hl7_message(wrapped)


def test_validate_hl7_message_outpatient_encounter_type(hl7_message: str) -> None:
    hl7 = hl7_message.replace("INPATIENT", "OUTPATIENT")
    wrapped = parse_hl7_message(hl7)
    assert wrapped is not None
