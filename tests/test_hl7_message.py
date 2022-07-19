from datetime import datetime

import pytest
from flask_batteries_included.helpers.timestamp import parse_datetime_to_iso8601
from flask_batteries_included.sqldb import db

from dhos_connector_api.models.hl7_message import Hl7Message


class TestHl7Message:
    def test_status_processed(self) -> None:
        message = Hl7Message()
        message.is_processed = False
        message.src_description = "tie"
        message.dst_description = "dhos"
        assert message.status == "received"
        message.src_description = "dhos"
        message.dst_description = "tie"
        assert message.status == "sent"
        message.is_processed = True
        assert message.status == "processed"

    def test_to_dict(self) -> None:
        sent_at = datetime.utcnow()
        msg = Hl7Message(
            content="decoded_content",
            message_control_id="1",
            message_type="ADT^A01",
            sent_at_=sent_at,
            is_processed=False,
            src_description="EPR",
            dst_description="DHOS",
            patient_identifiers={"NHS number": "1234567890"},
        )

        assert msg.to_dict() == {
            "message_control_id": "1",
            "content": "decoded_content",
            "message_type": "ADT^A01",
            "sent_at": parse_datetime_to_iso8601(sent_at),
            "is_processed": False,
            "src_description": "EPR",
            "dst_description": "DHOS",
            "uuid": None,
            "created": None,
            "created_by": None,
            "modified": None,
            "modified_by": None,
            "ack_status": None,
        }

    def test_to_dict_ack_status(self) -> None:
        sent_at = datetime.utcnow()
        msg = Hl7Message(
            content="decoded_content",
            message_control_id="1",
            message_type="ADT^A01",
            sent_at_=sent_at,
            is_processed=False,
            src_description="EPR",
            dst_description="DHOS",
            ack="MSH|^~\\&|OXON_TIE_ADT|OXON|c0481|OXON|20190702171301||ACK^A01|9183171301514230J4YP|P|2.3\rMSA|AA|TESTMSG3333",
            patient_identifiers={"NHS number": "1234567890"},
        )

        assert msg.to_dict() == {
            "message_control_id": "1",
            "content": "decoded_content",
            "message_type": "ADT^A01",
            "sent_at": parse_datetime_to_iso8601(sent_at),
            "is_processed": False,
            "src_description": "EPR",
            "dst_description": "DHOS",
            "uuid": None,
            "created": None,
            "created_by": None,
            "modified": None,
            "modified_by": None,
            "ack_status": "AA",
        }
