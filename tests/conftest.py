import base64
import collections
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional
from unittest import mock

import kombu_batteries_included
import pytest
from flask import Flask
from flask.ctx import AppContext
from mock import Mock
from pytest_mock import MockFixture

from dhos_connector_api.helpers import trustomer
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper
from dhos_connector_api.helpers.parser import parse_hl7_message


@pytest.fixture()
def app() -> Flask:
    """Fixture that creates app for testing"""
    import dhos_connector_api.app

    return dhos_connector_api.app.create_app(
        testing=True, use_pgsql=False, use_sqlite=True
    )


@pytest.fixture
def app_context(app: Flask) -> Generator[None, None, None]:
    with app.app_context():
        yield


class MaskType(collections.namedtuple("Mask", ["name", "code", "percent"])):
    @property
    def full_name(self) -> str:
        if self.percent == None:
            return self.name

        return f"{self.name} {self.percent}%"


@pytest.fixture
def mocked_publish(mocker: MockFixture) -> Mock:
    return mocker.patch.object(kombu_batteries_included, "publish_message")


@pytest.fixture(params=["a01"])
def hl7_message(request: Any) -> str:
    """Raw HL7 message of parameterised type"""
    msg_type = request.param
    assert isinstance(msg_type, str)
    data_dir = Path("tests/samples")
    file_to_open = data_dir / f"{msg_type.upper()}.hl7"
    with open(file_to_open, "r") as f:
        return f.read()


@pytest.fixture()
def hl7_encoded_message(hl7_message: str) -> str:
    """Base64 encoded HL7 message of parameterised type"""
    return base64.b64encode(hl7_message.encode(encoding="utf8")).decode("utf8")


@pytest.fixture()
def generate_ack() -> Callable:
    """
    This fixture returns a function that takes a b64 encoded hl7 message
    and returns the body of an ack message.
    """

    def create_ack_message(
        hl7_encoded: str,
        uuid: str,
        ack_code: str = "AA",
        error_code: str = "",
        error_msg: str = "",
    ) -> Dict:
        content: str = base64.b64decode(hl7_encoded).decode("utf8")
        message_wrapper = Hl7Wrapper(content)
        expected_ack_body = base64.b64encode(
            message_wrapper.generate_ack(
                ack_code=ack_code, error_code=error_code, error_msg=error_msg
            ).encode("utf8")
        ).decode("utf8")
        return {"uuid": uuid, "body": expected_ack_body, "type": "HL7v2"}

    return create_ack_message


@pytest.fixture(autouse=True)
def mock_create_ack(mocker: MockFixture, request: Any) -> None:
    """
    hl7 ack messages include date and time so tests can fail it time changes mid test
    this fixture simply replaces the actual ack body with a value that will remain constant
    during the test.

    The generated content is not intended to represent a genuine ack message.

    The fixture is autouse, so it applies to all tests including those
    defined by unittest.TestCase
    """
    if "nomockack" in request.keywords:
        return

    @mocker.patch("hl7.containers.Message.create_ack")
    def create_ack(
        self: Any,
        ack_code: str = "AA",
        message_id: Optional[str] = None,
        application: Optional[str] = None,
        facility: Optional[str] = None,
    ) -> str:
        return f"MSH|{repr(ack_code)}|{repr(message_id)}|{repr(application)}|{repr(facility)}"


@pytest.fixture
def date_of_birth() -> str:
    return "2002-11-23"


@pytest.fixture
def process_obs_set_message_body(mask_type: MaskType, date_of_birth: str) -> Dict:
    """
    A sample body for a process obs set message
    """
    return {
        "actions": [
            {
                "data": {
                    "clinician": {
                        "bookmarked_patients": [],
                        "bookmarks": [],
                        "can_edit_spo2_scale": False,
                        "created": "2019-02-04T12:32:18.333Z",
                        "created_by": {
                            "first_name": "system",
                            "last_name": "system",
                            "uuid": "I-AM-A-UUID",
                        },
                        "email_address": "jane.deer@test.com",
                        "first_name": "Jane",
                        "groups": ["GDMClinician"],
                        "job_title": "somejob",
                        "last_name": "Deer",
                        "locations": ["0c48a77f-393a-4abd-a083-9b0479ee445e"],
                        "login_active": True,
                        "modified": "2019-02-04T12:32:18.334Z",
                        "modified_by": {
                            "first_name": "system",
                            "last_name": "system",
                            "uuid": "I-AM-A-UUID",
                        },
                        "nhs_smartcard_number": "211214",
                        "phone_number": "07654123123",
                        "products": [
                            {
                                "closed_date": None,
                                "created": "2019-02-04T12:32:18.347Z",
                                "created_by": {
                                    "email_address": None,
                                    "first_name": "system",
                                    "last_name": "system",
                                    "locations": [],
                                    "nhs_smartcard_number": None,
                                    "phone_number": None,
                                    "uuid": "system",
                                },
                                "modified": "2019-02-04T12:32:18.347Z",
                                "modified_by": {
                                    "email_address": None,
                                    "first_name": "system",
                                    "last_name": "system",
                                    "locations": [],
                                    "nhs_smartcard_number": None,
                                    "phone_number": None,
                                    "uuid": "system",
                                },
                                "opened_date": "2019-02-04",
                                "product_name": "SEND",
                                "uuid": "c097e9ab-551b-45ca-b2a2-c7d57c721413",
                            }
                        ],
                        "send_entry_identifier": 123_456,
                        "terms_agreement": None,
                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                    },
                    "encounter": {
                        "admitted_at": "2018-07-25T11:00:00.000Z",
                        "created": "2018-01-02T00:00:00.000Z",
                        "discharged_at": "2018-07-25T21:39:00.000Z",
                        "encounter_type": "INPATIENT",
                        "epr_encounter_id": "2018L86699800",
                        "location_ods_code": "J-WD 5A^Bay A^Bed 1",
                        "location_uuid": "cebdb51e-1cb4-45c0-bc97-1a4359fa4a94",
                        "modified": "2018-01-02T00:00:00.000Z",
                        "patient_record_uuid": "1600e694-5077-48f3-ae3b-4d096efbb94e",
                        "score_system": "news2",
                        "uri": "http://uri.org",
                        "uuid": "896330df-eb9d-45d3-90cd-ded4b0230b92",
                    },
                    "observation_set": {
                        "created": "2019-01-31T09:47:27.123Z",
                        "created_by": {
                            "first_name": "Jane",
                            "last_name": "Deer",
                            "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                        },
                        "encounter_id": "9e1cd745-4c2b-4713-b9d1-588189358a03",
                        "is_partial": False,
                        "modified": "2019-01-31T09:47:27.123Z",
                        "modified_by": {
                            "first_name": "Jane",
                            "last_name": "Deer",
                            "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                        },
                        "monitoring_instruction": None,
                        "mins_late": -30,
                        "observations": [
                            {
                                "created": "2019-01-31T09:47:27.089Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:07:26.870Z",
                                "modified": "2019-01-31T09:47:27.089Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": None,
                                "observation_type": "spo2",
                                "observation_unit": "%",
                                "observation_value": 94,
                                "patient_refused": None,
                                "score_value": 0,
                                "uuid": "d449bc4f-b730-4ee2-b2a9-d1f70d8acab6",
                            },
                            {
                                "created": "2019-01-31T09:47:27.086Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:06:26.870Z",
                                "modified": "2019-01-31T09:47:27.086Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": None,
                                "observation_type": "heart_rate",
                                "observation_unit": "bpm",
                                "observation_value": None,
                                "patient_refused": True,
                                "score_value": 0,
                                "uuid": "87f9eef6-f76d-4cc6-a489-acefdf80a558",
                            },
                            {
                                "created": "2019-01-31T09:47:27.115Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:09:26.870Z",
                                "modified": "2019-01-31T09:47:27.115Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": {
                                    "created": "2019-01-31T09:47:27.117Z",
                                    "created_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "gcs_eyes": None,
                                    "gcs_motor": None,
                                    "gcs_verbal": None,
                                    "mask": None,
                                    "mask_percent": None,
                                    "modified": "2019-01-31T09:47:27.117Z",
                                    "modified_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "patient_position": "sitting",
                                    "uuid": "72e110eb-51a3-45bd-a97e-12c0261074b7",
                                },
                                "observation_string": None,
                                "observation_type": "diastolic_blood_pressure",
                                "observation_unit": "mmHg",
                                "observation_value": 152,
                                "patient_refused": None,
                                "uuid": "337dd2a9-8ab2-4c4f-baf5-5d4830c177ab",
                            },
                            {
                                "created": "2019-01-31T09:47:27.103Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:09:26.870Z",
                                "modified": "2019-01-31T09:47:27.103Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": "Pallor or Cyanosis",
                                "observation_type": "nurse_concern",
                                "observation_unit": None,
                                "observation_value": None,
                                "patient_refused": None,
                                "score_value": 3,
                                "uuid": "ab215a8c-e9c0-4fef-9058-9974cc4f602c",
                            },
                            {
                                "created": "2019-01-31T09:47:27.107Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:09:26.870Z",
                                "modified": "2019-01-31T09:47:27.108Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": {
                                    "created": "2019-01-31T09:47:27.110Z",
                                    "created_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "gcs_eyes": None,
                                    "gcs_motor": None,
                                    "gcs_verbal": None,
                                    "mask": None,
                                    "mask_percent": None,
                                    "modified": "2019-01-31T09:47:27.110Z",
                                    "modified_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "patient_position": "sitting",
                                    "uuid": "45bc2a7c-d19f-462b-9e97-451bb6ea7533",
                                },
                                "observation_string": None,
                                "observation_type": "systolic_blood_pressure",
                                "observation_unit": "mmHg",
                                "observation_value": 212,
                                "patient_refused": None,
                                "score_value": 1,
                                "uuid": "e5f9edfb-791e-41e9-b352-842defe3b135",
                            },
                            {
                                "created": "2019-01-31T09:47:27.094Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:06:26.870Z",
                                "modified": "2019-01-31T09:47:27.094Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": {
                                    "created": "2019-01-31T09:47:27.096Z",
                                    "created_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "gcs_eyes": None,
                                    "gcs_motor": None,
                                    "gcs_verbal": None,
                                    "mask": mask_type.name,
                                    "mask_percent": mask_type.percent,
                                    "modified": "2019-01-31T09:47:27.096Z",
                                    "modified_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "patient_position": None,
                                    "uuid": "20fcb37c-b8d4-45da-960d-b94de3b95301",
                                },
                                "observation_string": None,
                                "observation_type": "o2_therapy_status",
                                "observation_unit": "lpm",
                                "observation_value": 6.6,
                                "patient_refused": None,
                                "score_value": 5,
                                "uuid": "dca35b20-d3f8-4b96-b455-d81398a9623c",
                            },
                            {
                                "created": "2019-01-31T09:47:27.106Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:08:26.870Z",
                                "modified": "2019-01-31T09:47:27.106Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": None,
                                "observation_type": "respiratory_rate",
                                "observation_unit": "/min",
                                "observation_value": 10,
                                "patient_refused": None,
                                "score_value": 6,
                                "uuid": "c5d8bdb0-c7e6-4576-a54c-5a7381592521",
                            },
                            {
                                "created": "2019-01-31T09:47:27.092Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:09:26.870Z",
                                "modified": "2019-01-31T09:47:27.092Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": "Voice",
                                "observation_type": "consciousness_acvpu",
                                "observation_unit": None,
                                "observation_value": None,
                                "patient_refused": None,
                                "score_value": 7,
                                "uuid": "71095969-aa33-43d7-808d-907fe57c5c98",
                            },
                            {
                                "created": "2019-01-31T09:47:27.092Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:09:26.870Z",
                                "modified": "2019-01-31T09:47:27.092Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": {
                                    "created": "2019-01-31T09:47:27.096Z",
                                    "created_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "gcs_eyes": 4,
                                    "gcs_eyes_description": "Spontaneous",
                                    "gcs_motor": 6,
                                    "gcs_motor_description": "Obeys Commands",
                                    "gcs_verbal": 5,
                                    "gcs_verbal_description": "Oriented",
                                    "mask": None,
                                    "mask_percent": None,
                                    "modified": "2019-01-31T09:47:27.096Z",
                                    "modified_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "patient_position": None,
                                    "uuid": "20fcb37c-b8d4-45da-960d-b94de3b95301",
                                },
                                "observation_string": None,
                                "observation_type": "consciousness_gcs",
                                "observation_unit": None,
                                "observation_value": 15,
                                "patient_refused": None,
                                "score_value": 7,
                                "uuid": "71095969-aa33-43d7-808d-907fe57c5c98",
                            },
                            {
                                "created": "2019-01-31T09:47:27.102Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-01-30T13:09:26.870Z",
                                "modified": "2019-01-31T09:47:27.102Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": None,
                                "observation_type": "temperature",
                                "observation_unit": "celcius",
                                "observation_value": 34.9,
                                "patient_refused": None,
                                "score_value": 8,
                                "uuid": "1f428d18-ba74-4d01-836a-878afcb5ecaa",
                            },
                        ],
                        "record_time": "2019-01-30T13:06:26.870Z",
                        "score_severity": "medium",
                        "score_string": "Medium Score",
                        "score_system": "news2",
                        "score_value": 2,
                        "spo2_scale": 1,
                        "time_next_obs_set_due": "2022-02-03T11:02:04.110Z",
                        "uuid": "0324e62b-88fb-4aef-b15c-ee0454ce997f",
                        "empty_set": False,
                        "ranking": "0101010,2017-09-23T08:29:19.123+00:00",
                        "obx_reference_range": "0-4",
                        "obx_abnormal_flags": "HIGH",
                    },
                    "patient": {
                        "bookmarked": False,
                        "created": "2018-12-24T14:52:17.763Z",
                        "dh_products": [
                            {
                                "closed_date": None,
                                "closed_reason": None,
                                "closed_reason_other": None,
                                "created": "2018-12-24T14:52:17.706Z",
                                "opened_date": "2018-12-24",
                                "product_name": "SEND",
                                "uuid": "ac5266f0-5f5a-46f6-8268-3c53ff15445e",
                            }
                        ],
                        "dob": date_of_birth,
                        "first_name": "Ugi",
                        "hospital_number": "111111",
                        "last_name": "Maroon",
                        "nhs_number": "2222222222",
                        "record": {
                            "created": "2018-12-24T14:52:17.714Z",
                            "diagnoses": [],
                            "pregnancies": [],
                            "uuid": "1600e694-5077-48f3-ae3b-4d096efbb94e",
                        },
                        "sex": "248152002",
                        "uuid": "25e9c6e7-1b22-496d-9eda-6af919d7f254",
                    },
                },
                "name": "process_observation_set",
            }
        ]
    }


@pytest.fixture
def oru_message(
    message_control_id: str,
    sample_hl7_datetime: datetime,
    mask_type: MaskType,
    date_of_birth: str,
) -> str:
    """A generated ORU message, matching the data in process_obs_set_message_body"""
    if date_of_birth is None:
        date_of_birth = ""
    else:
        date_of_birth = date_of_birth.replace("-", "")

    message = f"""MSH|^~\\&|DHOS|SENSYNE|TRUST_TIE_ADT|TRUST|{sample_hl7_datetime}||ORU^R01^ORU_R01|{message_control_id}|P|2.6
PID|1|25e9c6e7-1b22-496d-9eda-6af919d7f254|111111^^^^MRN~2222222222^^^^NHS||Maroon^Ugi||{date_of_birth}|2
PV1|1||J-WD 5A^Bay A^Bed 1||||||||||||||||2018L86699800|||||||||||||||||||||||||20180725110000.000+0000
OBR|1||0324e62b-88fb-4aef-b15c-ee0454ce997f|EWS|||20190130130626.870+0000|||123456^Deer^Jane|||||||||||||||F
OBX|1|ST|ScoringSystem||NEWS2||||||F|||20190130130626.870+0000
OBX|2|ST|SpO2Scale||Scale 1||||||F|||20190130130626.870+0000
OBX|3|NM|TotalScore||2||0-4|HIGH|||F|||20190130130626.870+0000
OBX|4|ST|Severity||medium||||||F|||20190130130626.870+0000
OBX|5|TS|TimeNextObsSetDue||20220203110204.110+0000||||||F|||20190130130626.870+0000
OBX|6|NM|MinutesLate||-30||||||F|||20190130130626.870+0000
OBX|7|NM|HR||patient_refused|^bpm|||||F|||20190130130626.870+0000||123456^Deer^Jane
OBX|8|NM|HRScore||0||||||F|||20190130130626.870+0000
OBX|9|NM|RR||10|^/min|||||F|||20190130130826.870+0000||123456^Deer^Jane
OBX|10|NM|RRScore||6||||||F|||20190130130826.870+0000
OBX|11|NM|DBP||152|^mmHg|||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|12|NM|SBP||212|^mmHg|||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|13|NM|SBPScore||1||||||F|||20190130130926.870+0000
OBX|14|ST|BPPOS||sitting||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|15|NM|SPO2||94|^%|||||F|||20190130130726.870+0000||123456^Deer^Jane
OBX|16|NM|SPO2Score||0||||||F|||20190130130726.870+0000
OBX|17|NM|O2Rate||6.6|^lpm|||||F|||20190130130626.870+0000||123456^Deer^Jane
OBX|18|CE|O2Delivery||{mask_type.code}^{mask_type.full_name}||||||F|||20190130130626.870+0000||123456^Deer^Jane
OBX|19|NM|O2Score||5||||||F|||20190130130626.870+0000
OBX|20|NM|TEMP||34.9|^celcius|||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|21|NM|TEMPScore||8||||||F|||20190130130926.870+0000
OBX|22|CE|ACVPU||V^Voice||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|23|NM|ACVPUScore||7||||||F|||20190130130926.870+0000
OBX|24|CE|GCS-Eyes||4^Spontaneous||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|25|CE|GCS-Verbal||5^Oriented||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|26|CE|GCS-Motor||6^Obeys Commands||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|27|NM|GCS||15||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|28|ST|NC||Pallor or Cyanosis||||||F|||20190130130926.870+0000||123456^Deer^Jane"""
    return message.replace("\n", "\r")


@pytest.fixture
def meows_oru_message(
    message_control_id: str,
    sample_hl7_datetime: datetime,
    mask_type: MaskType,
    date_of_birth: Optional[str],
) -> str:
    if date_of_birth is None:
        date_of_birth = ""
    else:
        date_of_birth = date_of_birth.replace("-", "")

    message = f"""MSH|^~\\&|DHOS|SENSYNE|TRUST_TIE_ADT|TRUST|{sample_hl7_datetime}||ORU^R01^ORU_R01|{message_control_id}|P|2.6
PID|1|25e9c6e7-1b22-496d-9eda-6af919d7f254|111111^^^^MRN~2222222222^^^^NHS||Maroon^Ugi||{date_of_birth}|2
PV1|1||J-WD 5A^Bay A^Bed 1||||||||||||||||2018L86699800|||||||||||||||||||||||||20180725110000.000+0000
OBR|1||0324e62b-88fb-4aef-b15c-ee0454ce997f|EWS|||20190130130626.870+0000|||123456^Deer^Jane|||||||||||||||F
OBX|1|ST|ScoringSystem||MEOWS||||||F|||20190130130626.870+0000
OBX|2|NM|TotalScore||2||0-4|HIGH|||F|||20190130130626.870+0000
OBX|3|ST|Severity||medium||||||F|||20190130130626.870+0000
OBX|4|TS|TimeNextObsSetDue||20220203110204.110+0000||||||F|||20190130130626.870+0000
OBX|5|NM|MinutesLate||-30||||||F|||20190130130626.870+0000
OBX|6|NM|HR||patient_refused|^bpm|||||F|||20190130130626.870+0000||123456^Deer^Jane
OBX|7|NM|HRScore||0||||||F|||20190130130626.870+0000
OBX|8|NM|RR||10|^/min|||||F|||20190130130826.870+0000||123456^Deer^Jane
OBX|9|NM|RRScore||6||||||F|||20190130130826.870+0000
OBX|10|NM|DBP||152|^mmHg|||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|11|NM|DBPScore||2||||||F|||20190130130926.870+0000
OBX|12|NM|SBP||212|^mmHg|||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|13|NM|SBPScore||1||||||F|||20190130130926.870+0000
OBX|14|ST|BPPOS||sitting||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|15|NM|SPO2||94|^%|||||F|||20190130130726.870+0000||123456^Deer^Jane
OBX|16|NM|SPO2Score||0||||||F|||20190130130726.870+0000
OBX|17|NM|O2Rate||6.6|^lpm|||||F|||20190130130626.870+0000||123456^Deer^Jane
OBX|18|CE|O2Delivery||{mask_type.code}^{mask_type.full_name}||||||F|||20190130130626.870+0000||123456^Deer^Jane
OBX|19|NM|TEMP||34.9|^celcius|||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|20|NM|TEMPScore||8||||||F|||20190130130926.870+0000
OBX|21|CE|ACVPU||V^Voice||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|22|NM|ACVPUScore||7||||||F|||20190130130926.870+0000
OBX|23|CE|GCS-Eyes||4^Spontaneous||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|24|CE|GCS-Verbal||5^Oriented||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|25|CE|GCS-Motor||6^Obeys Commands||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|26|NM|GCS||15||||||F|||20190130130926.870+0000||123456^Deer^Jane
OBX|27|ST|NC||Pallor or Cyanosis||||||F|||20190130130926.870+0000||123456^Deer^Jane"""
    return message.replace("\n", "\r")


@pytest.fixture(
    params=[
        MaskType("Room Air", "RA", None),
        MaskType("Humidified", "H35", 35),
        MaskType("High Flow", "HIF21", None),
        MaskType("Venturi", "V28", 28),
    ],
    ids=["room-air", "humidified-35", "high-flow-21", "venturi-28"],
)
def mask_type(request: Any) -> MaskType:
    return request.param


@pytest.fixture()
def process_obs_set_message_body_sparse(mask_type: MaskType) -> Dict:
    """
    A sample body for a process obs set message, with sparse information
    """
    return {
        "actions": [
            {
                "data": {
                    "encounter": {
                        "admitted_at": "2019-05-23T11:27:18.483+04:00",
                        "created": "2018-01-02T00:00:00.000Z",
                        "discharged_at": "2018-07-25T21:39:00.000Z",
                        "encounter_type": "INPATIENT",
                        "location_ods_code": "BLARG",
                        "location_uuid": "cebdb51e-1cb4-45c0-bc97-1a4359fa4a94",
                        "modified": "2018-01-02T00:00:00.000Z",
                        "patient_record_uuid": "1600e694-5077-48f3-ae3b-4d096efbb94e",
                        "score_system": "news2",
                        "uri": "http://uri.org",
                        "uuid": "896330df-eb9d-45d3-90cd-ded4b0230b92",
                    },
                    "observation_set": {
                        "created": "2019-01-31T09:47:27.123Z",
                        "created_by": {
                            "first_name": "ReallyLong",
                            "last_name": "LAST&NAME",
                            "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                        },
                        "encounter_id": "9e1cd745-4c2b-4713-b9d1-588189358a03",
                        "is_partial": True,
                        "modified": "2019-01-31T09:47:27.123Z",
                        "modified_by": {
                            "first_name": "Jane",
                            "last_name": "Deer",
                            "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                        },
                        "monitoring_instruction": None,
                        "observations": [
                            {
                                "created": "2019-01-31T09:47:27.086Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-11-11T11:11:11.111-07:00",
                                "modified": "2019-01-31T09:47:27.086Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": None,
                                "observation_string": None,
                                "observation_type": "heart_rate",
                                "observation_unit": "bpm",
                                "observation_value": 250.0,
                                "patient_refused": None,
                                "score_value": 3,
                                "uuid": "87f9eef6-f76d-4cc6-a489-acefdf80a558",
                            },
                            {
                                "created": "2019-01-31T09:47:27.094Z",
                                "created_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "measured_time": "2019-11-11T11:11:11.111-07:00",
                                "modified": "2019-01-31T09:47:27.094Z",
                                "modified_by": {
                                    "first_name": "Jane",
                                    "last_name": "Deer",
                                    "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                },
                                "observation_metadata": {
                                    "created": "2019-01-31T09:47:27.096Z",
                                    "created_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "gcs_eyes": None,
                                    "gcs_motor": None,
                                    "gcs_verbal": None,
                                    "mask": mask_type.name,
                                    "mask_percent": mask_type.percent,
                                    "modified": "2019-01-31T09:47:27.096Z",
                                    "modified_by": {
                                        "first_name": "Jane",
                                        "last_name": "Deer",
                                        "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                                    },
                                    "patient_position": None,
                                    "uuid": "20fcb37c-b8d4-45da-960d-b94de3b95301",
                                },
                                "observation_string": None,
                                "observation_type": "o2_therapy_status",
                                "observation_unit": "lpm",
                                "observation_value": 0,
                                "patient_refused": None,
                                "score_value": 0,
                                "uuid": "dca35b20-d3f8-4b96-b455-d81398a9623c",
                            },
                        ],
                        "record_time": "2019-11-11T11:11:11.111-07:00",
                        "score_severity": "low-medium",
                        "score_string": "Low-Medium Score",
                        "score_system": "news2",
                        "score_value": 3,
                        "spo2_scale": 2,
                        "time_next_obs_set_due": None,
                        "uuid": "obs_set_uuid",
                        "empty_set": False,
                        "ranking": "0101010,2017-09-23T08:29:19.123+00:00",
                        "obx_reference_range": "0-4",
                        "obx_abnormal_flags": "N",
                    },
                    "patient": {
                        "bookmarked": False,
                        "created": "2018-12-24T14:52:17.763Z",
                        "dh_products": [
                            {
                                "closed_date": None,
                                "closed_reason": None,
                                "closed_reason_other": None,
                                "created": "2018-12-24T14:52:17.706Z",
                                "opened_date": "2018-12-24",
                                "product_name": "SEND",
                                "uuid": "ac5266f0-5f5a-46f6-8268-3c53ff15445e",
                            }
                        ],
                        "dob": "1912-01-31",
                        "first_name": "FIRST&NAME",
                        "hospital_number": "239847",
                        "last_name": "REALLYREALLYLONGLASTNAMEGOESHERE",
                        "record": {
                            "created": "2018-12-24T14:52:17.714Z",
                            "diagnoses": [],
                            "pregnancies": [],
                            "uuid": "1600e694-5077-48f3-ae3b-4d096efbb94e",
                        },
                        "sex": "32570681000036106",
                        "uuid": "some_patient_uuid",
                    },
                },
                "name": "process_observation_set",
            }
        ]
    }


@pytest.fixture
def oru_message_sparse(sample_hl7_datetime: str, mask_type: MaskType) -> str:
    """A generated ORU message, matching the data in process_obs_set_message_body_sparse"""
    message = f"""MSH|^~\\&|DHOS|SENSYNE|TRUST_TIE_ADT|TRUST|{sample_hl7_datetime}||ORU^R01^ORU_R01|0bcb18b24163b41f42e2|P|2.6
PID|1|some_patient_uuid|239847^^^^MRN||REALLYREALLYLONGLASTNAMEGOESHERE^FIRST\\T\\NAME||19120131|4
OBR|1||obs_set_uuid|EWS|||20191111181111.111+0000||||||||||||||||||F
OBX|1|ST|ScoringSystem||NEWS2||||||F|||20191111181111.111+0000
OBX|2|ST|SpO2Scale||Scale 2||||||F|||20191111181111.111+0000
OBX|3|NM|TotalScore||3||0-4|N|||F|||20191111181111.111+0000
OBX|4|ST|Severity||low-medium||||||F|||20191111181111.111+0000
OBX|5|NM|HR||250|^bpm|||||F|||20191111181111.111+0000
OBX|6|NM|HRScore||3||||||F|||20191111181111.111+0000
OBX|7|NM|O2Rate||0|^lpm|||||F|||20191111181111.111+0000
OBX|8|CE|O2Delivery||{mask_type.code}^{mask_type.full_name}||||||F|||20191111181111.111+0000
OBX|9|NM|O2Score||0||||||F|||20191111181111.111+0000"""
    return message.replace("\n", "\r")


@pytest.fixture()
def process_obs_set_message_body_spo2_change(mask_type: MaskType) -> Dict:
    """
    A sample body for a process obs set message, with sparse information
    """
    return {
        "actions": [
            {
                "data": {
                    "encounter": {
                        "admitted_at": "2019-05-23T11:27:18.483+04:00",
                        "created": "2018-01-02T00:00:00.000Z",
                        "discharged_at": "2018-07-25T21:39:00.000Z",
                        "encounter_type": "INPATIENT",
                        "location_ods_code": "BLARG",
                        "location_uuid": "cebdb51e-1cb4-45c0-bc97-1a4359fa4a94",
                        "modified": "2018-01-02T00:00:00.000Z",
                        "patient_record_uuid": "1600e694-5077-48f3-ae3b-4d096efbb94e",
                        "score_system": "news2",
                        "uri": "http://uri.org",
                        "uuid": "896330df-eb9d-45d3-90cd-ded4b0230b92",
                    },
                    "observation_set": {
                        "created": "2019-01-31T09:47:27.123Z",
                        "created_by": {
                            "first_name": "ReallyLong",
                            "last_name": "LAST&NAME",
                            "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                        },
                        "encounter_id": "9e1cd745-4c2b-4713-b9d1-588189358a03",
                        "modified": "2019-01-31T09:47:27.123Z",
                        "modified_by": {
                            "first_name": "Jane",
                            "last_name": "Deer",
                            "uuid": "4595c324-48e1-404a-be25-a18980223fd2",
                        },
                        "record_time": "2019-11-11T11:11:11.111-07:00",
                        "score_system": "news2",
                        "spo2_scale": 2,
                        "uuid": "obs_set_uuid",
                    },
                    "patient": {
                        "bookmarked": False,
                        "created": "2018-12-24T14:52:17.763Z",
                        "dh_products": [
                            {
                                "closed_date": None,
                                "closed_reason": None,
                                "closed_reason_other": None,
                                "created": "2018-12-24T14:52:17.706Z",
                                "opened_date": "2018-12-24",
                                "product_name": "SEND",
                                "uuid": "ac5266f0-5f5a-46f6-8268-3c53ff15445e",
                            }
                        ],
                        "dob": "1912-01-31",
                        "first_name": "FIRST&NAME",
                        "hospital_number": "239847",
                        "last_name": "REALLYREALLYLONGLASTNAMEGOESHERE",
                        "record": {
                            "created": "2018-12-24T14:52:17.714Z",
                            "diagnoses": [],
                            "pregnancies": [],
                            "uuid": "1600e694-5077-48f3-ae3b-4d096efbb94e",
                        },
                        "sex": "32570681000036106",
                        "uuid": "some_patient_uuid",
                    },
                },
                "name": "process_observation_set",
            }
        ]
    }


@pytest.fixture
def oru_message_spo2_change(sample_hl7_datetime: str, mask_type: MaskType) -> str:
    """A generated ORU message, matching the data in process_obs_set_message_body_sparse"""
    message = f"""MSH|^~\\&|DHOS|SENSYNE|TRUST_TIE_ADT|TRUST|{sample_hl7_datetime}||ORU^R01^ORU_R01|0bcb18b24163b41f42e2|P|2.6
PID|1|some_patient_uuid|239847^^^^MRN||REALLYREALLYLONGLASTNAMEGOESHERE^FIRST\\T\\NAME||19120131|4
OBR|1||obs_set_uuid|EWS|||20191111181111.111+0000||||||||||||||||||F
OBX|1|ST|ScoringSystem||NEWS2||||||F|||20191111181111.111+0000
OBX|2|ST|SpO2Scale||Scale 2||||||F|||20191111181111.111+0000"""
    return message.replace("\n", "\r")


@pytest.fixture
def mock_generate_message_control_id(
    mocker: MockFixture, message_control_id: str
) -> Mock:
    """A mocked method for generating a message control ID"""
    mock_generate = mocker.patch.object(Hl7Wrapper, "generate_message_control_id")
    mock_generate.return_value = message_control_id
    return mock_generate


@pytest.fixture
def message_control_id() -> str:
    """A message control ID for a MSH segment"""
    return "224ddf783bc4cc6c158f"


@pytest.fixture
def mock_hl7_datetime_now(mocker: MockFixture, sample_hl7_datetime: str) -> Mock:
    """A mocked method for getting the current time in HL7 format"""
    mock_now = mocker.patch.object(Hl7Wrapper, "generate_hl7_datetime_now")
    mock_now.return_value = sample_hl7_datetime
    return mock_now


@pytest.fixture
def sample_hl7_datetime() -> str:
    """An hl7 datetime string"""
    return "20190107123346.785+0000"


@pytest.fixture
def a01_message_wrapped() -> Hl7Wrapper:
    """Wrapped A01 message"""
    file_to_open = Path("tests/samples/A01.hl7")
    with open(file_to_open, "r") as f:
        msg = f.read()
    return parse_hl7_message(msg)


@pytest.fixture
def a34_message_wrapped() -> Hl7Wrapper:
    """Wrapped A34 message"""
    file_to_open = Path("tests/samples/A34.hl7")
    with open(file_to_open, "r") as f:
        msg = f.read()
    return parse_hl7_message(msg)


@pytest.fixture
def trustomer_config() -> Dict:
    return {
        "send_config": {
            "generate_oru_messages": True,
            "oxygen_masks": [
                {"code": "RA", "name": "Room Air"},
                {"code": "V{mask_percent}", "name": "Venturi"},
                {"code": "H{mask_percent}", "name": "Humidified"},
                {"code": "HIF{mask_percent}", "name": "High Flow"},
                {"code": "N", "name": "Nasal cann."},
                {"code": "SM", "name": "Simple"},
                {"code": "RM", "name": "Resv mask"},
                {"code": "TM", "name": "Trach."},
                {"code": "CP", "name": "CPAP"},
                {"code": "NIV", "name": "NIV"},
                {"code": "OPT", "name": "Optiflow"},
                {"code": "NM", "name": "Nebuliser"},
            ],
        },
        "hl7_config": {
            "outgoing_receiving_facility": "TRUST",
            "outgoing_receiving_application": "TRUST_TIE_ADT",
            "outgoing_timestamp_format": "%Y%m%d%H%M%S.%L%z",
            "outgoing_sending_application": "DHOS",
            "outgoing_sending_facility": "SENSYNE",
            "outgoing_processing_id": "P",
        },
    }


@pytest.fixture
def mock_trustomer_config(mocker: MockFixture, trustomer_config: Dict) -> mock.Mock:
    """Trustomer configuration"""
    return mocker.patch.object(
        trustomer, "get_trustomer_config", return_value=trustomer_config
    )


@pytest.fixture
def mock_bearer_authorization() -> Dict:
    from jose import jwt

    claims = {
        "sub": "1234567890",
        "name": "John Doe",
        "iat": 1_516_239_022,
        "iss": "http://localhost/",
    }
    token = jwt.encode(claims, "secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
