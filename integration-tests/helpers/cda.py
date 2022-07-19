from typing import Optional
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

DOCUMENT_NAMESPACE = "urn:hl7-org:v3"


def get_document_from_template(file_path: str, patient: dict, encounter: dict) -> str:
    ET.register_namespace("", DOCUMENT_NAMESPACE)
    tree = ET.parse(file_path)
    root: Element = tree.getroot()

    # patient details
    first_name: Optional[Element] = find_patient_first_name(root)
    if first_name is not None:
        first_name.text = patient["first_name"]

    last_name: Optional[Element] = find_patient_last_name(root)
    if last_name is not None:
        last_name.text = patient["last_name"]

    mrn: Optional[Element] = find_patient_mrn(root)
    if mrn is not None:
        mrn.set("extension", patient["nhs_number"])

    hospital_number: Optional[Element] = find_patient_hospital_number(root)
    if hospital_number is not None:
        hospital_number.set("extension", patient["hospital_number"])

    # encounter
    encounter_id: Optional[Element] = find_epr_encounter_id(root)
    if encounter_id is not None:
        encounter_id.set("code", encounter["epr_encounter_id"])

    return ET.tostring(root, encoding="unicode")


def _find_patient_name(parent: Element) -> Optional[Element]:
    return parent.find(
        f".//{{{DOCUMENT_NAMESPACE}}}patient/{{{DOCUMENT_NAMESPACE}}}name"
    )


def find_patient_first_name(parent: Element) -> Optional[Element]:
    child: Optional[Element] = _find_patient_name(parent)
    if child is not None:
        return child.find(f"./{{{DOCUMENT_NAMESPACE}}}given")
    return None


def find_patient_last_name(parent: Element) -> Optional[Element]:
    child: Optional[Element] = _find_patient_name(parent)
    if child is not None:
        return child.find(f"./{{{DOCUMENT_NAMESPACE}}}family")
    return None


def find_patient_mrn(parent: Element) -> Optional[Element]:
    return parent.find(
        f".//{{{DOCUMENT_NAMESPACE}}}patientRole/{{{DOCUMENT_NAMESPACE}}}id[@assigningAuthorityName='NHS']"
    )


def find_patient_hospital_number(parent: Element) -> Optional[Element]:
    return parent.find(
        f".//{{{DOCUMENT_NAMESPACE}}}patientRole/{{{DOCUMENT_NAMESPACE}}}id[@assigningAuthorityName='PAS']"
    )


def find_epr_encounter_id(parent: Element) -> Optional[Element]:
    return parent.find(
        f".//{{{DOCUMENT_NAMESPACE}}}encompassingEncounter/{{{DOCUMENT_NAMESPACE}}}code"
    )
