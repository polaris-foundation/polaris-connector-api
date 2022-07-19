from typing import Dict

from behave import given, step, then
from behave.runner import Context
from clients.rabbitmq_client import (
    create_rabbitmq_connection,
    create_rabbitmq_queue,
    get_rabbitmq_message,
)

RABBITMQ_MESSAGES = {"POST_HL7": "dhos.DM000009", "HL7_ACK": "dhos.24891000000101"}


@given("RabbitMQ is running")
def create_rabbit_queues(context: Context) -> None:
    if not hasattr(context, "rabbit_connection"):
        context.rabbit_connection = create_rabbitmq_connection()
        context.rabbit_queues = {
            RABBITMQ_MESSAGES["POST_HL7"]: create_rabbitmq_queue(
                queue_name="test-post",
                connection=context.rabbit_connection,
                routing_key=RABBITMQ_MESSAGES["POST_HL7"],
            ),
            RABBITMQ_MESSAGES["HL7_ACK"]: create_rabbitmq_queue(
                queue_name="test-ack",
                connection=context.rabbit_connection,
                routing_key=RABBITMQ_MESSAGES["HL7_ACK"],
            ),
        }


@step("(?P<an_or_no>an|no) internal message is published to RabbitMQ")
def get_message_from_queue(context: Context, an_or_no: str) -> None:
    assert an_or_no in ["an", "no"]
    message: Dict = get_rabbitmq_message(
        context.rabbit_queues[RABBITMQ_MESSAGES["HL7_ACK"]]
    )
    if an_or_no == "an":
        assert isinstance(message, Dict)
        assert "dhos_connector_message_uuid" in message
        assert message["dhos_connector_message_uuid"] == context.message_uuid
    else:
        assert message is None
