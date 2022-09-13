import uuid
from typing import Any, Dict, List

from behave import step
from behave.runner import Context
from clients import dhos_connector_api_client as api_client
from faker import Faker
from helpers import hl7
from helpers.clinician import clinician_factory
from helpers.encounter import encounter_factory
from helpers.observation import observation_set_factory
from helpers.patient import patient_factory
from helpers.person import Sex
from hl7apy.core import Message, Segment
from hl7apy.exceptions import ChildNotValid
from requests import Response
from she_logging import logger

OBS_TYPE_TO_OBX_IDENTIFIER: Dict[str, str] = {
    "consciousness_acvpu": "ACVPU",
    "o2_therapy_status": "O2Rate",
    "heart_rate": "HR",
    "respiratory_rate": "RR",
    "systolic_blood_pressure": "SBP",
    "diastolic_blood_pressure": "DBP",
    "spo2": "SPO2",
    "temperature": "TEMP",
    "nurse_concern": "NC",
}


@step("there exists an? (?P<data_type>.+)")
def generate_body(context: Context, data_type: str) -> None:
    data_type = data_type.replace(" ", "_")

    if data_type == "clinician":
        factory: Any = clinician_factory(
            groups=["SEND Clinician"],
            product_name="SEND",
            locations=["L1"],
            clinician_sex=Sex.FEMALE,
        )
        data: dict = factory()

    elif data_type == "patient":
        factory = patient_factory(
            locations=["L1"], product_name="SEND", patient_sex=Sex.MALE
        )
        data = factory()

    elif data_type == "encounter":
        factory = encounter_factory()
        data = factory(score_system="news2")
        data["location_ods_code"] = f"L{Faker().random_number(digits=7, fix_len=False)}"

    elif data_type == "observation_set":
        factory = observation_set_factory()
        data = factory()
        for obs in data["observations"]:
            if "score_value" not in obs:
                obs["score_value"] = 0

            if obs["patient_refused"]:
                obs["observation_string"] = None
                obs["observation_value"] = None

            if (
                obs["observation_type"] in ["consciousness_acvpu", "nurse_concern"]
                and "observation_value" not in obs
            ):
                obs["observation_value"] = None

    else:
        raise ValueError("I don't know how to generate %s body", data_type)

    data["uuid"] = str(uuid.uuid4())
    setattr(context, f"{data_type}_body", data)
    logger.debug("generated %s: %s", data_type, data)


@step("an ORU message is sent")
def send_oru_message(context: Context) -> None:
    message_body: dict = {
        "actions": [
            {
                "name": "process_observation_set",
                "data": {
                    "clinician": context.clinician_body,
                    "encounter": context.encounter_body,
                    "observation_set": context.observation_set_body,
                    "patient": context.patient_body,
                },
            }
        ]
    }
    response: Response = api_client.post_oru_message(
        jwt=context.system_jwt, body=message_body
    )
    response.raise_for_status()
    context.mrn = context.patient_body["hospital_number"]


@step("the ORU HL7 message contains patient data")
def assert_oru_h7_message(context: Context) -> None:
    message: Message = hl7.get_message_from_string(context.api_message["content"])

    # is this our patient?
    assert (
        context.patient_body["first_name"] == message.PID.patient_name.given_name.value
    )
    assert (
        context.patient_body["last_name"] == message.PID.patient_name.family_name.value
    )
    assert context.patient_body["hospital_number"] == message.PID.PID_3.id_number.value
    assert context.patient_body["uuid"] == message.PID.patient_id.value

    # is this our encounter?
    assert context.encounter_body["epr_encounter_id"] == message.PV1.VISIT_NUMBER.value
    assert (
        context.encounter_body["location_ods_code"]
        == message.PV1.ASSIGNED_PATIENT_LOCATION.value
    )

    # do we have our observations?
    for obs in context.observation_set_body["observations"]:
        if obs["observation_type"] in OBS_TYPE_TO_OBX_IDENTIFIER:
            logger.debug("observation: %s", obs)

            value: str = obs.get("observation_value")
            if value is None:
                value = obs.get("observation_string")

            if not obs["patient_refused"]:
                _assert_observation_in_obx(
                    message=message,
                    observation_identifier=OBS_TYPE_TO_OBX_IDENTIFIER[
                        obs["observation_type"]
                    ],
                    value=value,
                )
            else:
                logger.info("skipping value check due to patient refused")
        else:
            logger.warn(
                "Don't know where to find %s in OBX, skipping",
                obs["observation_type"],
            )


def _assert_observation_in_obx(
    message: Message, observation_identifier: str, value: str
) -> None:
    segment: List[Segment] = [
        s
        for s in message.OBX
        if s.OBSERVATION_IDENTIFIER.value == observation_identifier
    ]
    assert len(segment) == 1
    logger.debug("OBX: %s", segment[0].value)
    try:
        # acvpu and O2 delivery contain 2 fields such as "A^Alert" or "RA^Room Air"
        assert str(value) == str(segment[0].OBSERVATION_VALUE.OBX_5_2.value)
    except ChildNotValid:
        assert str(value) == str(segment[0].OBSERVATION_VALUE.OBX_5_1.value)
