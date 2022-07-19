import json
from typing import Dict, List

import requests
from environs import Env
from requests import Response, get, post

env = Env()
expected_trustomer = env.str("CUSTOMER_CODE").lower()
expected_product = "polaris"
expected_api_key = env.str("POLARIS_API_KEY")
trustomer_config = json.loads(env.str("MOCK_TRUSTOMER_CONFIG"))


def setup_mock_get_trustomer_config() -> None:
    payload = {
        "request": {
            "method": "GET",
            "url": "/dhos-trustomer/dhos/v1/trustomer/inttests",
            "headers": {
                "X-Trustomer": {"equalTo": expected_trustomer},
                "X-Product": {"equalTo": expected_product},
                "Authorization": {"equalTo": expected_api_key},
            },
        },
        "response": {"jsonBody": trustomer_config},
    }
    response = requests.post(f"http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def post_hl7_message_mock(response_body: Dict, status_code: int) -> None:
    payload: dict = {
        "request": {"method": "POST", "url": "/eprsa/epr/v1/hl7_message"},
        "response": {"status": status_code, "jsonBody": response_body},
    }
    response: Response = post(f"http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def post_mirth_soap_mock(response_body: str, status_code: int) -> None:
    payload: dict = {
        "request": {"method": "POST", "urlPathPattern": "/services/Mirth.*"},
        "response": {"status": status_code, "body": response_body},
    }
    response: Response = post(f"http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def post_mirth_xsd_mock(response_body: str, status_code: int) -> None:
    payload: dict = {
        "request": {"method": "GET", "url": "/services/Mirth?xsd=1"},
        "response": {"status": status_code, "body": response_body},
    }
    response: Response = post(f"http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def post_mirth_wsdl_mock(response_body: str, status_code: int) -> None:
    payload: dict = {
        "request": {"method": "GET", "url": "/services/Mirth?wsdl"},
        "response": {"status": status_code, "body": response_body},
    }
    response: Response = post(f"http://wiremock:8080/__admin/mappings", json=payload)
    response.raise_for_status()


def get_all_requests() -> List[Dict]:
    response: Response = get(f"http://wiremock:8080/__admin/requests")
    response.raise_for_status()
    return response.json()["requests"]
