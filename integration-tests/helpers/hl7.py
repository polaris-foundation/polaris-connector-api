from base64 import b64encode
from pathlib import Path
from typing import Dict, List

from hl7apy import parser
from hl7apy.core import Message, Segment
from she_logging import logger


def get_message_from_file(file_path: str) -> Message:
    path: Path = Path(file_path)
    return get_message_from_string(path.read_text().replace("\n", "\r"))


def get_message_from_string(string: str) -> Message:
    # Irrespective of `validation_level` or `force_validation`, parser.parse_message(string, find_groups=True) throws:
    # - InvalidEncodingChars when parsing generated AA messages
    # - UnsupportedVersion when parsing generated ORU_R01 messages
    #
    # hl7apy otherwise happily parses individual segments, hence parse individual segments.
    segments: List[Segment] = parser.parse_segments(string)
    logger.debug("segments: %s", segments)

    message = Message()
    # Message() adds its own MSH, override it
    message.MSH = segments.pop(0)
    for segment in segments:
        logger.debug("adding segment: %s", segment.value)
        message.add(segment)
    return message


def message_to_body(message: Message) -> Dict:
    return {
        "body": b64encode(message.value.replace("\r", "\n").encode("utf-8")).decode(
            "utf-8"
        ),
        "type": "HL7v2",
    }
