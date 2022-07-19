import base64
import datetime
from pathlib import Path
from typing import Callable, Dict
from unittest.mock import Mock

import draymed
import kombu_batteries_included
import pytest
from flask import Flask
from flask_batteries_included.helpers.error_handler import ServiceUnavailableException
from flask_batteries_included.sqldb import db
from freezegun import freeze_time
from pytest_mock import MockFixture

from dhos_connector_api.blueprint_api import receive_controller
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper
from dhos_connector_api.helpers.parser import parse_hl7_message
from dhos_connector_api.models.hl7_message import Hl7Message


@pytest.mark.usefixtures("app")
class TestHl7ReceiveController:
    @pytest.fixture(autouse=True)
    def mock_publish(self, mocker: MockFixture) -> Mock:
        return mocker.patch.object(kombu_batteries_included, "publish_message")

    @pytest.fixture
    def hl7_a01_encoded(self) -> str:
        hl7: str = Path("tests/samples/A01.hl7").read_text()
        return base64.b64encode(hl7.encode(encoding="utf8")).decode("utf8")

    @pytest.fixture
    def hl7_a01_ack(self, hl7_a01_encoded: str) -> str:
        message_wrapper = Hl7Wrapper(base64.b64decode(hl7_a01_encoded).decode("utf8"))
        return base64.b64encode(
            message_wrapper.generate_ack("AA").encode("utf8")
        ).decode("utf8")

    def test_bad_base64_encoding(self) -> None:
        msg: str = base64.b64encode(b"not valid base64")[:-1].decode("utf8")
        with pytest.raises(ValueError):
            receive_controller.create_and_process_hl7_message(msg)

    def test_create_hl7_missing_converter(
        self, app: Flask, hl7_a01_encoded: str
    ) -> None:
        app.config[
            "HL7_TRANSFORMER_MODULE"
        ] = "dhos_connector_api.blueprint_api.transformers.missing"
        with pytest.raises(ValueError):
            receive_controller.create_and_process_hl7_message(hl7_a01_encoded)

    @pytest.mark.nomockack
    def test_create_duplicate_hl7_message(self, hl7_a01_encoded: str) -> None:
        actual_first = receive_controller.create_and_process_hl7_message(
            hl7_a01_encoded
        )
        assert "MSA|AA|" in base64.b64decode(s=actual_first["body"]).decode("utf8")
        actual_second = receive_controller.create_and_process_hl7_message(
            hl7_a01_encoded
        )
        assert "MSA|AR|" in base64.b64decode(s=actual_second["body"]).decode("utf8")

    @pytest.mark.nomockack
    def test_create_duplicate_hl7_message_AR(
        self, mock_publish: Mock, hl7_a01_encoded: str
    ) -> None:
        decoded_message: str = base64.b64decode(hl7_a01_encoded).decode("utf8")
        message_wrapper = Hl7Wrapper(decoded_message)
        expected_second = message_wrapper.generate_ack(
            ack_code="AR",
            error_code="Hl7ApplicationRejectException",
            error_msg="HL7 message appears to be duplicate",
        ).encode("utf8")
        receive_controller.create_and_process_hl7_message(hl7_a01_encoded)
        actual_second = base64.b64decode(
            receive_controller.create_and_process_hl7_message(hl7_a01_encoded)[
                "body"
            ].encode("utf-8")
        )
        assert actual_second[:47].startswith(expected_second[:47])
        assert actual_second.endswith(expected_second[-49:])
        results = (
            Hl7Message.query.filter_by(content=decoded_message)
            .order_by(Hl7Message.created)
            .all()
        )
        assert len(results) == 2
        # Check both messages are in the database, with the latter marked as rejected.
        assert results[0].message_control_id is not None
        assert results[0].ack_status() == "AA"
        assert results[1].message_control_id is None
        assert results[1].ack_status() == "AR"

    def test_update_hl7_message(self, mock_publish: Mock) -> None:
        msg = Hl7Message(
            uuid="someuuid",
            content="something",
            message_control_id="1",
            message_type="ADT^A01",
            sent_at_=datetime.datetime.now(),
            is_processed=False,
            src_description="something",
            dst_description="something",
            patient_identifiers={"NHS number": "1234567890"},
        )
        db.session.add(msg)
        db.session.commit()
        data = {"is_processed": True}
        receive_controller.update_hl7_message("someuuid", data)
        device = Hl7Message.query.filter_by(uuid="someuuid").first_or_404()
        assert device.is_processed is True

    def test_create_hl7_success_a01(
        self,
        mock_publish: Mock,
        hl7_a01_encoded: str,
        hl7_a01_ack: str,
    ) -> None:

        actual = receive_controller.create_and_process_hl7_message(hl7_a01_encoded)
        expected = {
            "uuid": actual["uuid"],
            "body": hl7_a01_ack,
            "type": "HL7v2",
        }
        assert actual == expected

        mock_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={
                "dhos_connector_message_uuid": actual["uuid"],
                "actions": [
                    {
                        "name": "process_patient",
                        "data": {
                            "first_name": "STEPHEN",
                            "last_name": "ZZZEDUCATION",
                            "sex_sct": "248153007",
                            "nhs_number": "1239874560",
                            "mrn": "654321",
                            "date_of_birth": "1982-11-03",
                        },
                    },
                    {
                        "name": "process_location",
                        "data": {
                            "location": {
                                "epr_ward_code": "NOC-Ward B",
                                "epr_bay_code": "Day Room",
                                "epr_bed_code": "Chair 6",
                            }
                        },
                    },
                    {
                        "name": "process_encounter",
                        "data": {
                            "epr_encounter_id": "909127805",
                            "location": {
                                "epr_ward_code": "NOC-Ward B",
                                "epr_bay_code": "Day Room",
                                "epr_bed_code": "Chair 6",
                            },
                            "encounter_type": "INPATIENT",
                            "admitted_at": "2017-07-31T14:13:00.000Z",
                            "admission_cancelled": False,
                            "transfer_cancelled": False,
                            "discharge_cancelled": False,
                            "encounter_moved": False,
                            "patient_deceased": False,
                        },
                    },
                ],
            },
        )

    def test_create_hl7_success_a02(self, mock_publish: Mock) -> None:
        content: str = Path("tests/samples/A02.hl7").read_text()
        a02_encoded: str = base64.b64encode(content.encode(encoding="utf8")).decode(
            "utf8"
        )
        message_wrapper = Hl7Wrapper(content)
        expected_ack_body = base64.b64encode(
            message_wrapper.generate_ack("AA").encode("utf8")
        ).decode("utf8")

        actual = receive_controller.create_and_process_hl7_message(a02_encoded)
        expected = {"uuid": actual["uuid"], "body": expected_ack_body, "type": "HL7v2"}

        assert actual == expected

        mock_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={
                "dhos_connector_message_uuid": actual["uuid"],
                "actions": [
                    {
                        "name": "process_patient",
                        "data": {
                            "first_name": "STEPHEN",
                            "last_name": "ZZZASSESSMENTS",
                            "sex_sct": "248153007",
                            "mrn": "90462826",
                            "date_of_birth": "1982-11-03",
                        },
                    },
                    {
                        "name": "process_location",
                        "data": {
                            "location": {
                                "epr_ward_code": "J-WD 5A",
                                "epr_bay_code": "Room 01",
                                "epr_bed_code": "Bed A",
                            },
                            "previous_location": {
                                "epr_ward_code": "J-WD WWRecovery",
                                "epr_bay_code": "In Theatre",
                                "epr_bed_code": "Bed 01",
                            },
                        },
                    },
                    {
                        "name": "process_encounter",
                        "data": {
                            "epr_encounter_id": "907665208",
                            "location": {
                                "epr_ward_code": "J-WD 5A",
                                "epr_bay_code": "Room 01",
                                "epr_bed_code": "Bed A",
                            },
                            "encounter_type": "INPATIENT",
                            "admitted_at": "2017-02-01T14:27:00.000Z",
                            "admission_cancelled": False,
                            "transfer_cancelled": False,
                            "discharge_cancelled": False,
                            "encounter_moved": False,
                            "patient_deceased": False,
                            "previous_location": {
                                "epr_ward_code": "J-WD WWRecovery",
                                "epr_bay_code": "In Theatre",
                                "epr_bed_code": "Bed 01",
                            },
                        },
                    },
                ],
            },
        )

    def test_create_hl7_success_a03(self, mock_publish: Mock) -> None:
        content: str = Path("tests/samples/A03.hl7").read_text()
        a03_encoded: str = base64.b64encode(content.encode(encoding="utf8")).decode(
            "utf8"
        )
        message_wrapper = Hl7Wrapper(content)
        expected_ack_body = base64.b64encode(
            message_wrapper.generate_ack("AA").encode("utf8")
        ).decode("utf8")

        actual = receive_controller.create_and_process_hl7_message(a03_encoded)
        expected = {"uuid": actual["uuid"], "body": expected_ack_body, "type": "HL7v2"}
        assert actual == expected

        mock_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={
                "dhos_connector_message_uuid": actual["uuid"],
                "actions": [
                    {
                        "name": "process_patient",
                        "data": {
                            "first_name": "TEST",
                            "last_name": "ZZZWRIGHT",
                            "sex_sct": "248153007",
                            "mrn": "90462787",
                            "date_of_birth": "1912-01-01",
                        },
                    },
                    {
                        "name": "process_location",
                        "data": {
                            "location": {
                                "epr_ward_code": "J-WD Adam Bedfd",
                                "epr_bay_code": "A15",
                                "epr_bed_code": "A15",
                            },
                            "previous_location": {
                                "epr_ward_code": "J-WD Adam Bedfd",
                                "epr_bay_code": "A15",
                                "epr_bed_code": "A15",
                            },
                        },
                    },
                    {
                        "name": "process_encounter",
                        "data": {
                            "epr_encounter_id": "907665600",
                            "location": {
                                "epr_ward_code": "J-WD Adam Bedfd",
                                "epr_bay_code": "A15",
                                "epr_bed_code": "A15",
                            },
                            "encounter_type": "INPATIENT",
                            "admitted_at": "2017-04-03T12:21:00.000Z",
                            "admission_cancelled": False,
                            "transfer_cancelled": False,
                            "discharge_cancelled": False,
                            "encounter_moved": False,
                            "patient_deceased": False,
                            "discharged_at": "2017-04-28T13:35:00.000Z",
                            "previous_location": {
                                "epr_ward_code": "J-WD Adam Bedfd",
                                "epr_bay_code": "A15",
                                "epr_bed_code": "A15",
                            },
                        },
                    },
                ],
            },
        )

    def test_create_hl7_success_a08(self, mock_publish: Mock) -> None:
        content: str = Path("tests/samples/A08.hl7").read_text()
        a08_encoded: str = base64.b64encode(content.encode(encoding="utf8")).decode(
            "utf8"
        )
        message_wrapper = Hl7Wrapper(content)
        expected_ack_body = base64.b64encode(
            message_wrapper.generate_ack("AA").encode("utf8")
        ).decode("utf8")

        actual = receive_controller.create_and_process_hl7_message(a08_encoded)
        expected = {"uuid": actual["uuid"], "body": expected_ack_body, "type": "HL7v2"}
        assert actual == expected

        mock_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={
                "dhos_connector_message_uuid": actual["uuid"],
                "actions": [
                    {
                        "name": "process_patient",
                        "data": {
                            "first_name": "ZZZTEST",
                            "last_name": "ZZZTHISISBRANDNEW",
                            "sex_sct": "248152002",
                            "mrn": "90532297",
                            "date_of_birth": "1990-10-10",
                        },
                    }
                ],
            },
        )

    def test_create_hl7_success_a12(self, mock_publish: Mock) -> None:
        content: str = Path("tests/samples/A12.hl7").read_text()
        a12_encoded: str = base64.b64encode(content.encode(encoding="utf8")).decode(
            "utf8"
        )
        message_wrapper = Hl7Wrapper(content)
        expected_ack_body = base64.b64encode(
            message_wrapper.generate_ack("AA").encode("utf8")
        ).decode("utf8")

        actual = receive_controller.create_and_process_hl7_message(a12_encoded)
        expected = {"uuid": actual["uuid"], "body": expected_ack_body, "type": "HL7v2"}
        assert actual == expected

        mock_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={
                "dhos_connector_message_uuid": actual["uuid"],
                "actions": [
                    {
                        "name": "process_patient",
                        "data": {
                            "first_name": "TEST",
                            "last_name": "ZZZTEST",
                            "sex_sct": "248153007",
                            "nhs_number": "5900001865",
                            "mrn": "90462713",
                            "date_of_birth": "1989-08-19",
                        },
                    },
                    {
                        "name": "process_location",
                        "data": {
                            "location": {
                                "epr_ward_code": "O-WD CircleRead",
                                "epr_bay_code": "Bay 02",
                                "epr_bed_code": "Bed 01",
                            },
                            "previous_location": {
                                "epr_ward_code": "O-WD Manor",
                                "epr_bay_code": "Room 06",
                                "epr_bed_code": "Bed 01",
                            },
                        },
                    },
                    {
                        "name": "process_encounter",
                        "data": {
                            "epr_encounter_id": "907665490",
                            "location": {
                                "epr_ward_code": "O-WD CircleRead",
                                "epr_bay_code": "Bay 02",
                                "epr_bed_code": "Bed 01",
                            },
                            "encounter_type": "INPATIENT",
                            "admitted_at": "2017-03-08T17:07:00.000Z",
                            "admission_cancelled": False,
                            "transfer_cancelled": True,
                            "discharge_cancelled": False,
                            "encounter_moved": False,
                            "patient_deceased": False,
                            "previous_location": {
                                "epr_ward_code": "O-WD Manor",
                                "epr_bay_code": "Room 06",
                                "epr_bed_code": "Bed 01",
                            },
                        },
                    },
                ],
            },
        )

    def test_process_hl7_message_a01(self) -> None:
        hl7: str = Path("tests/samples/A01.hl7").read_text()
        encoded_message: bytes = base64.b64encode(hl7.encode(encoding="utf8"))
        decoded: str = base64.b64decode(encoded_message).decode("utf8")
        wrapped_message = parse_hl7_message(decoded)
        body = receive_controller.process_hl7_message("sone_uuid", wrapped_message)
        assert body["actions"][0]["data"]["first_name"] == "STEPHEN"
        assert body["actions"][1]["data"]["location"]["epr_ward_code"] == "NOC-Ward B"

    def test_process_hl7_message_a02(self) -> None:
        hl7: str = Path("tests/samples/A02.hl7").read_text()
        encoded_message: bytes = base64.b64encode(hl7.encode(encoding="utf8"))
        decoded: str = base64.b64decode(encoded_message).decode("utf8")
        wrapped_message = parse_hl7_message(decoded)
        body = receive_controller.process_hl7_message("some_uuid", wrapped_message)
        assert body["actions"][1]["data"]["location"]["epr_ward_code"] == "J-WD 5A"
        assert (
            body["actions"][1]["data"]["previous_location"]["epr_ward_code"]
            == "J-WD WWRecovery"
        )

    def test_process_hl7_message_a34(self) -> None:
        hl7: str = Path("tests/samples/A34.hl7").read_text()
        encoded_message: bytes = base64.b64encode(hl7.encode(encoding="utf8"))
        decoded: str = base64.b64decode(encoded_message).decode("utf8")
        wrapped_message = parse_hl7_message(decoded)
        body = receive_controller.process_hl7_message("msg_uuid", wrapped_message)
        assert body["actions"][0]["data"]["previous_mrn"] == "90532399"
        assert body["actions"][0]["data"]["mrn"] == "90532398"

    def test_process_hl7_message_a11(self) -> None:
        hl7: str = Path("tests/samples/A11.hl7").read_text()
        encoded_message: bytes = base64.b64encode(hl7.encode(encoding="utf8"))
        decoded: str = base64.b64decode(encoded_message).decode("utf8")
        wrapped_message = parse_hl7_message(decoded)
        body = receive_controller.process_hl7_message("some_uuid", wrapped_message)
        assert body["actions"][0]["data"]["mrn"] == "12345"
        assert body["actions"][2]["data"]["admission_cancelled"] is True

    def test_process_hl7_message_missing_gender(self) -> None:
        hl7: str = Path("tests/samples/A01.hl7").read_text()
        hl7 = hl7.replace(
            "||ZZZEDUCATION^STEPHEN^^^^^CURRENT||19821103|1||",
            "||ZZZEDUCATION^STEPHEN^^^^^CURRENT||19821103|||",
        )
        encoded_message: bytes = base64.b64encode(hl7.encode(encoding="utf8"))
        decoded: str = base64.b64decode(encoded_message).decode("utf8")
        wrapped_message = parse_hl7_message(decoded)
        body = receive_controller.process_hl7_message("some_uuid", wrapped_message)
        assert body["actions"][0]["data"]["sex_sct"] == draymed.codes.code_from_name(
            "unknown", "sex"
        )

    def test_process_hl7_message_indeterminate_gender(self) -> None:
        hl7: str = Path("tests/samples/A01.hl7").read_text()
        hl7 = hl7.replace(
            "||ZZZEDUCATION^STEPHEN^^^^^CURRENT||19821103|1||",
            "||ZZZEDUCATION^STEPHEN^^^^^CURRENT||19821103|4||",
        )
        encoded_message: bytes = base64.b64encode(hl7.encode(encoding="utf8"))
        decoded: str = base64.b64decode(encoded_message).decode("utf8")
        wrapped_message = parse_hl7_message(decoded)
        body = receive_controller.process_hl7_message("some_uuid", wrapped_message)
        assert body["actions"][0]["data"]["sex_sct"] == draymed.codes.code_from_name(
            "indeterminate", "sex"
        )

    A13_PARSED_ACTIONS = [
        {
            "name": "process_patient",
            "data": {
                "first_name": "ZZZTEST",
                "last_name": "ZZZRUSS",
                "sex_sct": "248153007",
                "mrn": "90532016",
                "date_of_birth": "1988-10-10",
            },
        },
        {
            "name": "process_location",
            "data": {
                "location": {
                    "epr_ward_code": "J-ED",
                    "epr_bay_code": None,
                    "epr_bed_code": None,
                },
                "previous_location": {
                    "epr_ward_code": "J-ED",
                    "epr_bay_code": None,
                    "epr_bed_code": None,
                },
            },
        },
        {
            "name": "process_encounter",
            "data": {
                "epr_encounter_id": "909127352",
                "location": {
                    "epr_ward_code": "J-ED",
                    "epr_bay_code": None,
                    "epr_bed_code": None,
                },
                "encounter_type": "EMERGENCY",
                "admitted_at": "2017-05-31T14:02:00.000Z",
                "admission_cancelled": False,
                "transfer_cancelled": False,
                "discharge_cancelled": True,
                "encounter_moved": False,
                "patient_deceased": False,
                "previous_location": {
                    "epr_ward_code": "J-ED",
                    "epr_bay_code": None,
                    "epr_bed_code": None,
                },
            },
        },
    ]
    A31_PARSED_ACTIONS = [
        {
            "name": "process_patient",
            "data": {
                "first_name": "LIZTWO",
                "last_name": "ZZZWILSONE",
                "sex_sct": "248152002",
                "mrn": "90532072",
                "date_of_birth": "1980-01-01",
            },
        }
    ]
    A34_PARSED_ACTIONS = [
        {
            "name": "process_patient",
            "data": {
                "first_name": "DUCK",
                "last_name": "ZZZTEST",
                "sex_sct": "248152002",
                "date_of_birth": "1990-01-01",
                "mrn": "90532398",
                "previous_mrn": "90532399",
            },
        }
    ]
    A35_PARSED_ACTIONS = [
        {
            "name": "process_patient",
            "data": {
                "first_name": "Ugi",
                "last_name": "Maroon",
                "sex_sct": "248152002",
                "mrn": "1111111",
                "nhs_number": "2222222222",
                "date_of_birth": "2002-11-23",
                # We don't currently parse the account number, nor the previous account_number.
                # If we did, they might be here
                # "account_number": "9852156",
                # "previous_account_number": "5858614",
            },
        },
        {
            "name": "process_location",
            "data": {
                "location": {
                    "epr_ward_code": "J-WD Gynae",
                    "epr_bay_code": "Side Room 6",
                    "epr_bed_code": "Bed 01",
                }
            },
        },
        {
            "name": "process_encounter",
            "data": {
                "epr_encounter_id": "11194968",
                "epr_previous_location_code": "",
                "parent_encounter_id": "11194968",
                "location": {
                    "epr_ward_code": "J-WD Gynae",
                    "epr_bay_code": "Side Room 6",
                    "epr_bed_code": "Bed 01",
                },
                "encounter_type": "INPATIENT",
                "admitted_at": "2018-07-25T11:00:00.000Z",
                "admission_cancelled": False,
                "transfer_cancelled": False,
                "discharge_cancelled": False,
                "discharged_at": "2018-07-25T21:39:00.000Z",
                "encounter_moved": False,
                "patient_deceased": False,
            },
        },
    ]

    @pytest.mark.parametrize(
        "hl7_message,actions",
        [
            ("a13", A13_PARSED_ACTIONS),
            ("a31", A31_PARSED_ACTIONS),
            ("a34", A34_PARSED_ACTIONS),
            ("a35", A35_PARSED_ACTIONS),
        ],
        indirect=["hl7_message"],
    )
    def test_create_hl7_success(
        self,
        mocked_publish: Mock,
        generate_ack: Callable,
        hl7_encoded_message: str,
        actions: Dict,
    ) -> None:
        actual = receive_controller.create_and_process_hl7_message(hl7_encoded_message)
        uuid = actual["uuid"]

        expected = generate_ack(hl7_encoded_message, uuid)
        assert expected == actual

        mocked_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={"dhos_connector_message_uuid": uuid, "actions": actions},
        )

    @pytest.mark.parametrize(
        "hl7_message,actions,msg_ctrl_id",
        [
            ("a13", A13_PARSED_ACTIONS, "Q543961008T545123385X16159A1096"),
            ("a31", A31_PARSED_ACTIONS, "Q548420607T549582984A1096"),
            ("a34", A34_PARSED_ACTIONS, "Q550010220T551172597C21234508A1096"),
            ("a35", A35_PARSED_ACTIONS, "Q783011522T784178135C7978505A1096"),
        ],
        indirect=["hl7_message"],
    )
    def test_get_hl7_message_by_message_control_id(
        self,
        mocked_publish: Mock,
        generate_ack: Callable,
        hl7_encoded_message: str,
        actions: Dict,
        msg_ctrl_id: str,
    ) -> None:
        actual = receive_controller.create_and_process_hl7_message(hl7_encoded_message)
        uuid = actual["uuid"]

        expected = generate_ack(hl7_encoded_message, uuid)
        assert expected == actual

        mocked_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={"dhos_connector_message_uuid": uuid, "actions": actions},
        )

        messages = receive_controller.get_hl7_message_by_message_control_id(msg_ctrl_id)

        assert len(messages) == 1
        assert messages[0]["uuid"] == uuid

    @pytest.mark.parametrize(
        "hl7_message,actions,identifier",
        [
            ("a13", A13_PARSED_ACTIONS, "90532016"),
            ("a31", A31_PARSED_ACTIONS, "90532072"),
            ("a34", A34_PARSED_ACTIONS, "90532398"),
            ("a35", A35_PARSED_ACTIONS, "1111111"),
        ],
        indirect=["hl7_message"],
    )
    def test_get_hl7_message_by_identifier(
        self,
        mocked_publish: Mock,
        generate_ack: Callable,
        hl7_encoded_message: str,
        actions: Dict,
        identifier: str,
    ) -> None:
        actual = receive_controller.create_and_process_hl7_message(hl7_encoded_message)
        uuid = actual["uuid"]

        expected = generate_ack(hl7_encoded_message, uuid)
        assert expected == actual

        mocked_publish.assert_called_with(
            routing_key="dhos.24891000000101",
            body={"dhos_connector_message_uuid": uuid, "actions": actions},
        )

        messages = receive_controller.get_hl7_message_by_identifier(
            identifier_type="MRN", identifier=identifier
        )

        assert len(messages) == 1
        assert messages[0]["uuid"] == uuid

    def test_patient_identifiers_stored(self) -> None:
        content: str = Path("tests/samples/A01.hl7").read_text()
        a01_encoded: str = base64.b64encode(content.encode(encoding="utf8")).decode(
            "utf8"
        )
        result = receive_controller.create_and_process_hl7_message(a01_encoded)
        message = Hl7Message.query.filter_by(uuid=result["uuid"]).first()
        assert message.patient_identifiers == {
            "NHS number": "1239874560",
            "MRN": "654321",
            "Visit ID": "909127805",
        }

    @pytest.mark.nomockack
    def test_message_with_unexpected_error_is_rejected(
        self, mock_publish: Mock
    ) -> None:
        """
        Tests that we appropriately reject a message (ACK AE) that unexpectedly raises an error when validating
        or processing - specifically, in this case, an unparseable datetime of 000000000000.
        """
        hl7: str = "\n".join(
            [
                r"MSH|^~\&|CSCLRC|RJC|TIE|RJC|20201028110221|912591490046|ADT^A12^ADT_A09|12345|P|2.3|53617806||",
                r"PID|1||123456^^^^MRN~1234567890^^^^NHS||TEST^Patient^A^^MRS||19480704000000|2",
                r"PV1|1|INPATIENT||||||||||||||||INPATIENT||||||||||||000000|||||000000|||||||||000000000000",
            ]
        )
        encoded_message: str = base64.b64encode(hl7.encode(encoding="utf8")).decode(
            "utf8"
        )
        actual = receive_controller.create_and_process_hl7_message(encoded_message)
        decoded_ack = base64.b64decode(actual["body"]).decode("utf8")
        assert "|AE|" in decoded_ack
        assert mock_publish.call_count == 0
