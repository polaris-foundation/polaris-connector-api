from typing import Any, Dict, Optional

from flask_batteries_included.helpers.timestamp import (
    parse_datetime_to_iso8601,
    parse_iso8601_to_datetime,
)
from flask_batteries_included.sqldb import ModelIdentifier, db

import dhos_connector_api.helpers.parser


class Hl7Message(ModelIdentifier, db.Model):

    content = db.Column(db.String, nullable=True, unique=False)
    message_type = db.Column(db.String, nullable=True, unique=False)
    sent_at_ = db.Column(db.DateTime, nullable=True, unique=False)
    is_processed = db.Column(db.Boolean, nullable=False, unique=False, default=False)
    src_description = db.Column(db.String, nullable=True, unique=False)
    dst_description = db.Column(db.String, nullable=True, unique=False)
    message_control_id = db.Column(db.String, nullable=True, unique=True, index=True)
    ack = db.Column(db.String, nullable=True, unique=False)
    patient_identifiers = db.Column(db.JSON, nullable=True, unique=False)

    def __init__(self, **kwargs: Any) -> None:
        # Constructor to satisfy linters.
        super(Hl7Message, self).__init__(**kwargs)

    @property
    def status(self) -> str:
        if self.is_processed:
            return "processed"
        if self.src_description == "dhos":
            return "sent"
        return "received"

    @property
    def sent_at(self) -> Optional[str]:
        return parse_datetime_to_iso8601(self.sent_at_)

    @sent_at.setter
    def sent_at(self, v: str) -> None:
        self.sent_at_ = parse_iso8601_to_datetime(v)

    def ack_status(self) -> Optional[str]:
        """
        Returns the status field in the ACK message. Expected values are: "AA", "AR", "AE" and None
        """
        if not self.ack:
            return None
        try:
            hl7_wrapper = dhos_connector_api.helpers.parser.parse_hl7_message(self.ack)
            return hl7_wrapper.get_field_by_hl7_path("MSA.F1")
        except ValueError:
            return None

    def to_dict(self) -> dict:
        message = {
            "content": self.content,
            "message_type": self.message_type,
            "sent_at": self.sent_at,
            "is_processed": self.is_processed,
            "src_description": self.src_description,
            "dst_description": self.dst_description,
            "message_control_id": self.message_control_id,
            "ack_status": self.ack_status(),
        }
        return {**message, **self.pack_identifier()}

    @classmethod
    def schema(cls) -> Dict:
        return {"updatable": {"is_processed": bool}}
