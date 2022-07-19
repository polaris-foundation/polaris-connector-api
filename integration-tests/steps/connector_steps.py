import uuid
from typing import Dict

from behave import step, then, when
from behave.runner import Context
from clients import dhos_connector_api_client as api_client
from clients import wiremock_client
from clients.rabbitmq_client import get_rabbitmq_message
from faker import Faker
from helpers.hl7 import get_message_from_file, message_to_body
from hl7apy.core import Message
from requests import Response
from she_logging import logger
from steps.rabbitmq_steps import RABBITMQ_MESSAGES


@step("the Trustomer API is running")
def setup_mock_trustomer_api(context: Context) -> None:
    wiremock_client.setup_mock_get_trustomer_config()


@step("a duplicate HL7 message is sent")
def send_duplicate_hl7_message(context: Context) -> None:
    response: Response = api_client.post_message(
        jwt=context.system_jwt, body=context.message_body
    )
    response.raise_for_status()
    response_json = response.json()
    assert "uuid" in response_json
    context.message_uuid = response_json["uuid"]


@step("a valid HL7 message is sent")
def send_valid_hl7_message(context: Context) -> None:
    message: Message = get_message_from_file("./resources/admit_body.hl7")
    message_control_id: str = str(uuid.uuid4()).upper().replace("-", "")
    message.MSH.message_control_id = message_control_id
    context.message_control_id = message_control_id

    fake = Faker()
    new_mrn: str = str(fake.random_number(digits=6, fix_len=False))
    context.mrn = new_mrn
    logger.debug("patient MRN: %s", new_mrn)

    assert message.PID.PID_2.PID_2_5.value == "MRN"
    message.PID.PID_2.PID_2_1.value = new_mrn

    # MRN is also in PID.PID_3, it is usually on index 0 but just in case, let's find where the MRN actually is
    field = [f for f in message.PID.PID_3 if f.PID_3_5.value == "MRN"]
    assert len(field) == 1
    field[0].PID_3_1.value = new_mrn
    context.message_body = message_to_body(message)
    response: Response = api_client.post_message(
        jwt=context.system_jwt, body=context.message_body
    )
    response.raise_for_status()
    response_json = response.json()
    assert "uuid" in response_json
    context.message_uuid = response_json["uuid"]


@then("the API responds with an (?P<ack_type>.+) ACK message")
def read_message(context: Context, ack_type: str) -> None:
    response: Response = api_client.get_message_by_uuid(
        jwt=context.system_jwt, uuid=context.message_uuid
    )
    response.raise_for_status()
    message = response.json()
    assert isinstance(message, Dict)
    assert "ack_status" in message
    assert message["ack_status"].upper() == ack_type


@step("the message (?P<action>can be found|is retrieved) by its Message Control ID")
def assert_message_found_by_mcid(context: Context, action: str) -> None:
    response: Response = api_client.get_message_by_control_id(
        jwt=context.system_jwt, control_id=context.message_control_id
    )
    response.raise_for_status()
    message: dict = response.json()
    logger.debug("message by mrn: %s", message)

    if action == "can be found":
        # assert that we've found the right message
        assert context.message_control_id == message[0]["message_control_id"]
        assert context.message_uuid == message[0]["uuid"]
    context.api_message = message[0]


@step("the message (?P<action>can be found|is retrieved) by its MRN")
def assert_message_found_by_mrn(context: Context, action: str) -> None:
    response: Response = api_client.get_message_by_identifier(
        jwt=context.system_jwt, identifier_type="MRN", identifier=context.mrn
    )
    response.raise_for_status()
    message: dict = response.json()
    logger.debug("message by mrn: %s", message)

    assert isinstance(message, list)
    assert len(message) == 1
    if action == "can be found":
        # assert that we've found the right message
        assert context.message_control_id == message[0]["message_control_id"]
        assert context.message_uuid == message[0]["uuid"]
    context.api_message = message[0]


@step("the message (?P<action>can be found|is retrieved) by its uuid")
def assert_message_found_by_uuid(context: Context, action: str) -> None:
    response: Response = api_client.get_message_by_uuid(
        jwt=context.system_jwt, uuid=context.message_uuid
    )
    response.raise_for_status()
    message: dict = response.json()
    logger.debug("message by uuid: %s", message)

    if action == "can be found":
        # assert that we've found the right message
        assert context.message_control_id == message["message_control_id"]
        assert context.message_uuid == message["uuid"]
    context.api_message = message
