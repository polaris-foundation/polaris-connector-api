import json
import os
from datetime import datetime
from typing import Dict, Optional

import hl7
import pytz
from flask_batteries_included.helpers.timestamp import (
    parse_date_to_iso8601,
    parse_datetime_to_iso8601,
    parse_iso8601_to_datetime,
)
from hl7 import generate_message_control_id as _generate_message_control_id
from she_logging import logger

from dhos_connector_api.helpers import trustomer


class Hl7Wrapper:
    """
    This class abstracts whatever library we are using to do the HL7 message parsing. It's not to be
    confused with the HL7Message model, which is what is persisted in the database.
    """

    def __init__(self, raw_message: str):
        self.raw_message = raw_message
        self.parsed = hl7.parse(raw_message)

    def contains_segment(self, segment_id: str) -> bool:
        # Well, this sucks.
        try:
            self.parsed.segment(segment_id)
            return True
        except KeyError:
            return False

    def get_field_by_hl7_path(self, path: str, default: str = None) -> Optional[str]:
        # Well, this also sucks.
        try:
            field = str(self.parsed[path])
            if field == '""':
                # Empty HL7 field containing just quote marks.
                return default
            return field
        except (KeyError, IndexError, ValueError):
            return default

    def get_iso8601_datetime_by_hl7_path(
        self, path: str, default_timezone: str = "UTC"
    ) -> Optional[str]:
        hl7_timestamp: Optional[str] = self.get_field_by_hl7_path(path)
        if hl7_timestamp is None:
            return None
        try:
            dt: datetime = hl7.datatypes.parse_datetime(hl7_timestamp)
        except ValueError:
            # Let this bubble up, but add a logging message to explain the problem.
            logger.error("Couldn't parse HL7 datetime")
            raise
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = pytz.timezone(default_timezone).localize(dt)
        return parse_datetime_to_iso8601(dt)

    def get_iso8601_date_by_hl7_path(self, path: str) -> Optional[str]:
        hl7_timestamp: Optional[str] = self.get_field_by_hl7_path(path, default=None)
        dt: datetime = hl7.datatypes.parse_datetime(hl7_timestamp)
        if dt is None:
            return None
        return parse_date_to_iso8601(dt.date())

    def get_json_string(self) -> str:
        return json.dumps(self.parsed)

    def get_message_type_field(self) -> str:
        # e.g. "ADT^A01"
        return str(self.parsed.segment("MSH")[9])

    def get_message_datetime_iso8601(
        self, default_timezone: str = "UTC"
    ) -> Optional[str]:
        return self.get_iso8601_datetime_by_hl7_path(
            "MSH.F7", default_timezone=default_timezone
        )

    def get_patient_identifier(
        self, identifier_type: str, default: str = None
    ) -> Optional[str]:
        # Get the value of a patient identifier from the PID segment,
        # given a identifier type such as "MRN" or "NHS".
        identifiers_to_search = [identifier_type]
        if identifier_type == "NHS":
            identifiers_to_search = ["NHS", "NHSNBR", "NHSNMBR"]

        for i in range(len(self.parsed.segment("PID")[3])):
            pid = self.get_field_by_hl7_path(f"PID.F3.R{i+1}.C5", default=default)
            if pid in identifiers_to_search:
                return self.get_field_by_hl7_path(f"PID.F3.R{i+1}.C1", default=default)
        return default

    def get_merged_patient_identifier(
        self, identifier_type: str, default: str = None
    ) -> Optional[str]:
        # Get the value of a previously used patient identifier from the MRG segment,
        # given a identifier type such as "MRN" or "NHS".
        identifiers_to_search = [identifier_type]
        if identifier_type == "NHS":
            identifiers_to_search = ["NHS", "NHSNBR", "NHSNMBR"]

        for i in range(len(self.parsed.segment("MRG")[1])):
            pid = self.get_field_by_hl7_path(f"MRG.F1.R{i+1}.C5", default=default)
            if pid in identifiers_to_search:
                return self.get_field_by_hl7_path(f"MRG.F1.R{i+1}.C1", default=default)
        return default

    def get_message_control_id(self) -> Optional[str]:
        return self.get_field_by_hl7_path("MSH.F10.R1.C1")

    def generate_ack(
        self, ack_code: str, error_code: str = "", error_msg: str = ""
    ) -> str:
        ack: str = str(self.parsed.create_ack(ack_code))
        if error_msg or error_code:
            ack += f"\nERR|||{error_code}|E||||{error_msg}"
        return ack

    def get_patient_identifiers_as_dict(self) -> Dict:
        return {
            "NHS number": self.get_patient_identifier("NHS"),
            "MRN": self.get_patient_identifier("MRN"),
            "Visit ID": self.get_field_by_hl7_path("PV1.F19"),
        }

    @classmethod
    def generate_message_control_id(cls) -> str:
        return _generate_message_control_id()

    @classmethod
    def generate_hl7_datetime_now(
        cls, server_tz: str = os.environ["SERVER_TIMEZONE"]
    ) -> str:
        server_timezone = pytz.timezone(server_tz)
        current_time = datetime.now(server_timezone)
        ans = cls.hl7_datetime_format(current_time)
        return ans

    @classmethod
    def iso8601_to_hl7_datetime(
        cls, iso8601: str, server_tz: str = os.environ["SERVER_TIMEZONE"]
    ) -> str:
        dt = parse_iso8601_to_datetime(iso8601)
        if dt is None:
            return ""

        stc = pytz.timezone(server_tz)
        dt = dt.astimezone(stc)
        return cls.hl7_datetime_format(dt)

    @classmethod
    def hl7_datetime_format(cls, date_time: datetime) -> str:
        trustomer_config: Dict = trustomer.get_trustomer_config()
        timestamp_format: str = trustomer_config["hl7_config"][
            "outgoing_timestamp_format"
        ]
        if "%L" in timestamp_format:
            # We use %L as a custom strftime formatter referring to milliseconds.
            sections = [date_time.strftime(s) for s in timestamp_format.split("%L")]
            millis = date_time.strftime("%f")[:-3]
            return millis.join(sections)
        return date_time.strftime(timestamp_format)
