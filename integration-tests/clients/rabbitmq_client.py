from typing import Dict, Optional

from environs import Env
from kombu import Connection, Exchange, Message, Queue
from kombu.utils import json


def create_rabbitmq_connection() -> Connection:
    env = Env()
    host: str = env.str("RABBITMQ_HOST", "rabbitmq")
    port: int = env.int("RABBITMQ_PORT", 5672)
    username: str = env.str("RABBITMQ_USERNAME", "guest")
    password: str = env.str("RABBITMQ_PASSWORD", "guest")
    conn_string: str = f"amqp://{username}:{password}@{host}:{port}//"
    return Connection(conn_string)


def create_rabbitmq_queue(
    connection: Connection, queue_name: str, routing_key: str
) -> Queue:
    exchange = Exchange("dhos", "topic")
    queue = Queue(
        name=queue_name, exchange=exchange, routing_key=routing_key, channel=connection
    )
    queue.declare()
    return queue


def get_rabbitmq_message(queue: Queue) -> Optional[Dict]:
    message: Message = queue.get()
    if message is not None:
        message.ack()
        return json.loads(message.body)
    return None


def purge_rabbitmq_queue(queue: Queue) -> None:
    queue.purge()
