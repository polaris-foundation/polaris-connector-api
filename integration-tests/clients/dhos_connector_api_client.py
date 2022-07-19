from typing import Dict

from environs import Env
from requests import Response, get, post
from she_logging import logger


def _get_base_url() -> str:
    return Env().str("DHOS_CONNECTOR_API_HOST", "http://dhos-connector-api:5000")


def _get_auth_headers(jwt: str) -> Dict:
    return {"Authorization": f"Bearer {jwt}"}


def post_message(jwt: str, body: Dict) -> Response:
    response: Response = post(
        f"{_get_base_url()}/dhos/v1/message",
        headers=_get_auth_headers(jwt),
        json=body,
        timeout=15,
    )
    logger.debug("post message returned: %s", response.text)
    return response


def post_cda_message(jwt: str, content: str) -> Response:
    response: Response = post(
        f"{_get_base_url()}/dhos/v1/cda_message",
        headers=_get_auth_headers(jwt),
        json={"content": content, "type": "HL7v3CDA"},
        timeout=15,
    )
    logger.debug("post CDA message status code: %s", response.status_code)
    return response


def post_oru_message(jwt: str, body: Dict) -> Response:
    response: Response = post(
        f"{_get_base_url()}/dhos/v1/oru_message",
        headers=_get_auth_headers(jwt),
        json=body,
        timeout=15,
    )
    logger.debug("post ORU message status code: %s", response.status_code)
    return response


def get_message_by_uuid(jwt: str, uuid: str) -> Response:
    return get(
        f"{_get_base_url()}/dhos/v1/message/{uuid}",
        headers=_get_auth_headers(jwt),
        timeout=15,
    )


def get_message_by_identifier(
    jwt: str, identifier_type: str, identifier: str
) -> Response:
    return get(
        f"{_get_base_url()}/dhos/v1/message/search",
        params={"identifier_type": identifier_type, "identifier": identifier},
        headers=_get_auth_headers(jwt),
        timeout=15,
    )


def get_message_by_control_id(jwt: str, control_id: str) -> Response:
    return get(
        f"{_get_base_url()}/dhos/v1/message/search/{control_id}",
        headers=_get_auth_headers(jwt),
        timeout=15,
    )
