from typing import Dict, List, Optional

import pytest
from pytest_mock import MockFixture

from dhos_connector_api.helpers import generator, trustomer
from dhos_connector_api.helpers.errors import Hl7ApplicationErrorException
from dhos_connector_api.helpers.parser import generate_patient_action, parse_hl7_message


@pytest.mark.usefixtures(
    "app",
    "mock_generate_message_control_id",
    "mock_hl7_datetime_now",
    "mock_trustomer_config",
)
class TestGenerator:
    def test_generate_patient_action_missing_patient_identifier(
        self, hl7_message: str
    ) -> None:
        hl7 = hl7_message.replace("654321^^^NOC-MRN^MRN^", "654321^^^NOC-XXX^XXX^")
        hl7 = hl7.replace("NHSNBR", "XXXXXX")
        hl7 = hl7.replace("NHSNMBR", "XXXXXXX")
        wrapped = parse_hl7_message(hl7)
        with pytest.raises(Hl7ApplicationErrorException):
            generate_patient_action(wrapped)

    @pytest.mark.parametrize("date_of_birth", ["2002-11-23", None])
    def test_generate_oru_message_valid(
        self,
        process_obs_set_message_body: Dict,
        oru_message: str,
        date_of_birth: Optional[str],
    ) -> None:
        data = process_obs_set_message_body["actions"][0]["data"]
        result = generator.generate_oru_message(
            patient=data["patient"],
            encounter=data["encounter"],
            obs_set=data["observation_set"],
            clinician=data["clinician"],
        )
        assert result == oru_message

    def test_generate_oru_message_sparse(
        self, process_obs_set_message_body_sparse: Dict, oru_message_sparse: str
    ) -> None:
        data = process_obs_set_message_body_sparse["actions"][0]["data"]
        result = generator.generate_oru_message(
            patient=data["patient"],
            encounter=data["encounter"],
            obs_set=data["observation_set"],
        )
        assert result == oru_message_sparse

    def test_generate_oru_message_spo2_change(
        self,
        process_obs_set_message_body_spo2_change: Dict,
        oru_message_spo2_change: str,
    ) -> None:
        data = process_obs_set_message_body_spo2_change["actions"][0]["data"]
        result = generator.generate_oru_message(
            patient=data["patient"],
            encounter=data["encounter"],
            obs_set=data["observation_set"],
        )
        assert result == oru_message_spo2_change

    def test_generate_oru_message_receiver(
        self,
        mocker: MockFixture,
        process_obs_set_message_body: Dict,
        oru_message: str,
        trustomer_config: Dict,
    ) -> None:
        trustomer_config["hl7_config"]["outgoing_receiving_facility"] = "HL7_IS_BAD"
        trustomer_config["hl7_config"]["outgoing_receiving_application"] = "REALLY_BAD"
        mocker.patch.object(
            trustomer, "get_trustomer_config", return_value=trustomer_config
        )
        data = process_obs_set_message_body["actions"][0]["data"]
        result = generator.generate_oru_message(
            patient=data["patient"],
            encounter=data["encounter"],
            obs_set=data["observation_set"],
            clinician=data["clinician"],
        )
        expected = oru_message.replace("TRUST_TIE_ADT|TRUST", "REALLY_BAD|HL7_IS_BAD")
        assert result == expected

    def test_generate_oru_message_garbage(self) -> None:
        with pytest.raises(KeyError):
            generator.generate_oru_message(
                patient={"key": "value"},
                encounter={"key": "value"},
                obs_set={"key": "value"},
                clinician={"key": "value"},
            )

    def test_generate_oru_message_unknown_score_system(
        self, process_obs_set_message_body: Dict
    ) -> None:
        data = process_obs_set_message_body["actions"][0]["data"]
        data["observation_set"]["score_system"] = "JEWS"  # Jon's Early Warning Score
        with pytest.raises(ValueError) as excinfo:
            generator.generate_oru_message(
                patient=data["patient"],
                encounter=data["encounter"],
                obs_set=data["observation_set"],
                clinician=data["clinician"],
            )
        assert str(excinfo.value) == "Unexpected score system 'JEWS'"

    def test_generate_obx_gcs(self, process_obs_set_message_body: Dict) -> None:
        obs_set: Dict = process_obs_set_message_body["actions"][0]["data"][
            "observation_set"
        ]
        gcs_observation: Dict = next(
            o
            for o in obs_set["observations"]
            if o["observation_type"] == "consciousness_gcs"
        )
        del gcs_observation["observation_metadata"]["gcs_eyes"]
        del gcs_observation["observation_metadata"]["gcs_verbal"]
        gcs_observation["observation_metadata"]["gcs_motor"] = 4
        gcs_observation["observation_metadata"][
            "gcs_motor_description"
        ] = "Normal Flexion"
        gcs_observation["observation_value"] = 13
        result: List[str] = generator._generate_obx_gcs(
            obs_list=obs_set["observations"], collector="someone", start_idx=1
        )
        assert len(result) == 2
        assert result[0].startswith("OBX|1|CE|GCS-Motor||4^Normal Flexion|")
        assert result[1].startswith("OBX|2|NM|GCS||13|")

    def test_generate_obx_hr(self, process_obs_set_message_body: Dict) -> None:
        hr_obs = process_obs_set_message_body["actions"][0]["data"]["observation_set"][
            "observations"
        ][1]
        obs_set: List[Dict] = [hr_obs]
        result: List[str] = generator._generate_obx_hr(
            obs_list=obs_set, collector="someone", start_idx=1
        )
        assert len(result) == 2
        assert result[0].startswith("OBX|1|NM|HR||patient_refused|")
        assert result[1].startswith("OBX|2|NM|HRScore||0|")

    @pytest.mark.parametrize(
        "input_str,output_str",
        [
            ("T&T", "T\\T\\T"),
            ("\\^&|~", "\\E\\\\S\\\\T\\\\F\\\\R\\"),
            ("I^HATE||HL7", "I\\S\\HATE\\F\\\\F\\HL7"),
            ("no-op", "no-op"),
        ],
    )
    def test_hl7_escape(self, input_str: str, output_str: str) -> None:
        assert generator._hl7_escape(input_str) == output_str

    def test_generate_meows_oru_message(
        self, process_obs_set_message_body: Dict, meows_oru_message: str
    ) -> None:
        data = process_obs_set_message_body["actions"][0]["data"]
        data["observation_set"]["score_system"] = "meows"
        data["observation_set"].pop("spo2_scale", None)
        data["observation_set"]["observations"][2]["score_value"] = 2
        data["observation_set"]["observations"][5].pop("score_value", None)
        result = generator.generate_oru_message(
            patient=data["patient"],
            encounter=data["encounter"],
            obs_set=data["observation_set"],
            clinician=data["clinician"],
        )
        assert result == meows_oru_message

    def test_generate_obx_nc(self, process_obs_set_message_body: Dict) -> None:
        nc_obs = process_obs_set_message_body["actions"][0]["data"]["observation_set"][
            "observations"
        ][3]
        obs_set: List[Dict] = [nc_obs]
        result: List[str] = generator._generate_obx_nurse_concern(
            obs_list=obs_set, collector="someone", start_idx=1
        )
        assert len(result) == 1
        assert result[0].startswith(
            "OBX|1|ST|NC||Pallor or Cyanosis||||||F|||20190130130926.870+0000||someone"
        )

    def test_generate_obx_multi_nc(self, process_obs_set_message_body: Dict) -> None:
        nc_obs = process_obs_set_message_body["actions"][0]["data"]["observation_set"][
            "observations"
        ][3]
        nc_obs["observation_string"] = "Infection?, Pallor or Cyanosis"
        obs_set: List[Dict] = [nc_obs]
        result: List[str] = generator._generate_obx_nurse_concern(
            obs_list=obs_set, collector="someone", start_idx=1
        )
        assert len(result) == 2
        assert result[0].startswith(
            "OBX|1|ST|NC||Infection?||||||F|||20190130130926.870+0000||someone"
        )
        assert result[1].startswith(
            "OBX|2|ST|NC||Pallor or Cyanosis||||||F|||20190130130926.870+0000||someone"
        )

    def test_generate_obx_multi_nc_no_space(
        self, process_obs_set_message_body: Dict
    ) -> None:
        nc_obs = process_obs_set_message_body["actions"][0]["data"]["observation_set"][
            "observations"
        ][3]
        nc_obs["observation_string"] = "Infection?,Pallor or Cyanosis"
        obs_set: List[Dict] = [nc_obs]
        result: List[str] = generator._generate_obx_nurse_concern(
            obs_list=obs_set, collector="someone", start_idx=1
        )
        assert len(result) == 2
        assert result[0].startswith(
            "OBX|1|ST|NC||Infection?||||||F|||20190130130926.870+0000||someone"
        )
        assert result[1].startswith(
            "OBX|2|ST|NC||Pallor or Cyanosis||||||F|||20190130130926.870+0000||someone"
        )
