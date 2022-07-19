from typing import Dict, List, Optional
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from behave import step
from behave.runner import Context
from clients import dhos_connector_api_client as api_client
from clients import wiremock_client
from helpers import cda
from requests import Response
from she_logging import logger

ENVELOPE_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
MIRTH_ACCEPT_MESSAGE_NAMESPACE = "http://ws.connectors.connect.mirth.com/"


@step("a CDA message is sent")
def send_cda_message(context: Context) -> None:
    document: str = cda.get_document_from_template(
        file_path="./resources/clinical_document.xml",
        patient=context.patient_body,
        encounter=context.encounter_body,
    )
    response: Response = api_client.post_cda_message(
        jwt=context.system_jwt, content=document
    )
    response.raise_for_status()
    context.cda_document = document


@step("the sent CDA message is received by the receiving system")
def assert_message_is_received(context: Context) -> None:
    # find the CDA document for our encounter, this will be in our mock Mirth
    all_requests: List[Dict] = wiremock_client.get_all_requests()
    logger.info(
        "searching for encounter %s", context.encounter_body["epr_encounter_id"]
    )

    doc_root = None
    for req in all_requests:
        doc_root = _get_document_xml_from_response(req)
        logger.debug("doc root: %s", doc_root)
        if (
            doc_root is not None
            and cda.find_epr_encounter_id(doc_root).get("code")
            == context.encounter_body["epr_encounter_id"]
        ):
            break

    assert doc_root is not None
    assert (
        context.patient_body["first_name"] == cda.find_patient_first_name(doc_root).text
    )
    assert (
        context.patient_body["last_name"] == cda.find_patient_last_name(doc_root).text
    )
    assert context.patient_body["nhs_number"] == cda.find_patient_mrn(doc_root).get(
        "extension"
    )
    assert context.patient_body["hospital_number"] == cda.find_patient_hospital_number(
        doc_root
    ).get("extension")


def _get_document_xml_from_response(response: Dict) -> Optional[Element]:
    try:
        root: Element = ET.fromstring(response["request"]["body"])
        body: Optional[Element] = root.find(f".//{{{ENVELOPE_NAMESPACE}}}Body")
        if body is not None:
            document: Optional[Element] = body.find(
                f".//{{{MIRTH_ACCEPT_MESSAGE_NAMESPACE}}}acceptMessage/arg0"
            )
            if document is not None:
                return ET.fromstring(str(document.text))
    except ET.ParseError:
        pass
    return None
