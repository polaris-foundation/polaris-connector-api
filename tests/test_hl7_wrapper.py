from typing import Dict

import pytest
from flask.ctx import AppContext
from pytest_mock import MockFixture

from dhos_connector_api.helpers import trustomer
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper


class TestHl7Wrapper:
    def test_contains_segment(self, a01_message_wrapped: Hl7Wrapper) -> None:
        assert a01_message_wrapped.contains_segment("ZZZ") is False
        assert a01_message_wrapped.contains_segment("PV1") is True

    def test_get_field_by_hl7_path(self, a01_message_wrapped: Hl7Wrapper) -> None:
        assert a01_message_wrapped.get_field_by_hl7_path("ZZZ.F5.R1.C1") is None
        assert (
            a01_message_wrapped.get_field_by_hl7_path("PID.F5.R1.C1") == "ZZZEDUCATION"
        )

    def test_get_json_string(self, a01_message_wrapped: Hl7Wrapper) -> None:
        assert len(a01_message_wrapped.get_json_string()) == 3354

    def test_get_message_type_field(self, a01_message_wrapped: Hl7Wrapper) -> None:
        assert a01_message_wrapped.get_message_type_field() == "ADT^A01"

    def test_get_message_datetime(self, a01_message_wrapped: Hl7Wrapper) -> None:
        assert (
            a01_message_wrapped.get_message_datetime_iso8601()
            == "2017-07-31T14:13:48.000Z"
        )

    def test_get_iso8601_datetime_by_hl7_path(
        self, a01_message_wrapped: Hl7Wrapper
    ) -> None:
        dt = a01_message_wrapped.get_iso8601_datetime_by_hl7_path("PV1.F44", "UTC")
        assert dt == "2017-07-31T14:13:00.000Z"

    def test_get_iso8601_datetime_by_hl7_path_localised(
        self, a01_message_wrapped: Hl7Wrapper
    ) -> None:
        dt = a01_message_wrapped.get_iso8601_datetime_by_hl7_path(
            "PV1.F44", "Europe/London"
        )
        assert dt == "2017-07-31T14:13:00.000+01:00"

    def test_get_iso8601_datetime_by_hl7_path_none(
        self, a01_message_wrapped: Hl7Wrapper
    ) -> None:
        dt = a01_message_wrapped.get_iso8601_datetime_by_hl7_path("ZZZ.F1", "UTC")
        assert dt is None

    def test_get_iso8601_date_by_hl7_path(
        self, a01_message_wrapped: Hl7Wrapper
    ) -> None:
        dt = a01_message_wrapped.get_iso8601_date_by_hl7_path("EVN.F2")
        assert dt == "2017-07-31"

    def test_get_patient_identifier_success(
        self, a01_message_wrapped: Hl7Wrapper
    ) -> None:
        mrn = a01_message_wrapped.get_patient_identifier("MRN")
        assert mrn == "654321"
        nhs = a01_message_wrapped.get_patient_identifier("NHS")
        assert nhs == "1239874560"
        zzz = a01_message_wrapped.get_patient_identifier("ZZZ")
        assert zzz is None
        yyy = a01_message_wrapped.get_patient_identifier("YYY", "QQQ")
        assert yyy == "QQQ"

    def test_get_merged_patient_identifier(
        self, a34_message_wrapped: Hl7Wrapper
    ) -> None:
        mrn = a34_message_wrapped.get_merged_patient_identifier("MRN")
        assert mrn == "90532399"
        nhs = a34_message_wrapped.get_merged_patient_identifier("NHS")
        assert nhs is None
        zzz = a34_message_wrapped.get_merged_patient_identifier("ZZZ")
        assert zzz is None
        yyy = a34_message_wrapped.get_merged_patient_identifier("YYY", default="QQQ")
        assert yyy == "QQQ"

    def test_iso8601_to_hl7_datetime_short_format(
        self, mocker: MockFixture, trustomer_config: Dict
    ) -> None:
        trustomer_config["hl7_config"]["outgoing_timestamp_format"] = "%Y%m%d%H%M%S"
        mocker.patch.object(
            trustomer, "get_trustomer_config", return_value=trustomer_config
        )
        iso8601 = "2019-10-22T00:02:03.456+0000"
        assert Hl7Wrapper.iso8601_to_hl7_datetime(iso8601) == "20191022000203"

    def test_iso8601_to_hl7_datetime_long_format(
        self, mocker: MockFixture, trustomer_config: Dict
    ) -> None:
        trustomer_config["hl7_config"][
            "outgoing_timestamp_format"
        ] = "%Y%m%d%H%M%S.%L%z"
        mocker.patch.object(
            trustomer, "get_trustomer_config", return_value=trustomer_config
        )
        iso8601 = "2019-10-22T01:02:03.456+0100"
        assert Hl7Wrapper.iso8601_to_hl7_datetime(iso8601) == "20191022000203.456+0000"

    @pytest.mark.parametrize(
        "tz, expected",
        [
            ("US/Eastern", "20190821200203"),
            ("Europe/London", "20190822010203"),
            ("UTC", "20190822000203"),
        ],
    )
    @pytest.mark.freeze_time("2019-08-22T01:02:03.456+0100")
    def test_generate_hl7_datetime_now(
        self,
        app_context: AppContext,
        mocker: MockFixture,
        trustomer_config: Dict,
        tz: str,
        expected: str,
    ) -> None:
        trustomer_config["hl7_config"]["outgoing_timestamp_format"] = "%Y%m%d%H%M%S"
        mocker.patch.object(
            trustomer, "get_trustomer_config", return_value=trustomer_config
        )
        hl7_datetime = Hl7Wrapper.generate_hl7_datetime_now(tz)
        assert hl7_datetime == expected

    @pytest.mark.nomockack
    def test_AR_ack_generate(self, a01_message_wrapped: Hl7Wrapper) -> None:
        ack_msg = a01_message_wrapped.generate_ack(
            ack_code="AR", error_code="error_code", error_msg="this is an error"
        )
        assert ack_msg.startswith("MSH|^~\\&|OXON_TIE_ADT|OXON|c0481")
        assert ack_msg.endswith("ERR|||error_code|E||||this is an error")
