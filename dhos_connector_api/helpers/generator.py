from hashlib import md5
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from flask_batteries_included.helpers.timestamp import parse_iso8601_to_date
from she_logging import logger

from dhos_connector_api.helpers import trustomer
from dhos_connector_api.helpers.converters import parse_sct_to_sex
from dhos_connector_api.helpers.hl7_wrapper import Hl7Wrapper

VALID_EWS_SCORE_SYSTEMS: Set[str] = {"NEWS2", "MEOWS"}


def generate_oru_message(
    patient: Dict, encounter: Dict, obs_set: Dict, clinician: Dict = None
) -> str:

    # Generates an ORU message for an observation set, consisting of:
    # 1) A MSH (message header) segment
    # 2) A PID (patient identifier) segment
    # 3) An OBR (observation request) segment
    # 4) A series of OBX segments for the obs and their scores

    # TODO: BP posture OBX segment
    # TODO: attending doctor in PV1

    logger.debug("Generating ORU message for obs set with UUID %s", obs_set["uuid"])

    # Build field to contain information about the person who recorded the obs.
    if clinician:
        clinician_identifier = clinician["send_entry_identifier"]
        clinician_last_name = _hl7_escape(clinician["last_name"])
        clinician_first_name = _hl7_escape(clinician["first_name"])
        collector: Optional[
            str
        ] = f"{clinician_identifier}^{clinician_last_name}^{clinician_first_name}"
    else:
        # We don't have any info on who took the obs.
        logger.warning(
            "No clinician information, ORU message will not contain collector field"
        )
        collector = None

    obs_list: List[Dict] = obs_set.get("observations", [])
    msg_ctrl_id: str = md5(
        obs_set["uuid"].encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:20]

    segment_msh = _generate_msh_segment(msg_ctrl_id=msg_ctrl_id)
    segment_pid = _generate_pid_segment(patient=patient)
    segment_obr = _generate_obr_segment(obs_set=obs_set, collector=collector)
    segment_pv1 = _generate_pv1_segment(encounter=encounter)

    # Generate OBX (observation) segments.
    segment_obx: List[str] = []
    segment_obx.extend(
        _generate_obx_overall_score(obs_set, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_time_next_due(obs_set, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(_generate_obx_mins_late(obs_set, start_idx=len(segment_obx) + 1))
    segment_obx.extend(
        _generate_obx_hr(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_rr(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_dbp(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_sbp(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_bp_posture(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_spo2(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_o2_therapy(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_temp(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_acvpu(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_gcs(obs_list, collector, start_idx=len(segment_obx) + 1)
    )
    segment_obx.extend(
        _generate_obx_nurse_concern(obs_list, collector, start_idx=len(segment_obx) + 1)
    )

    oru_message_segments = [segment_msh, segment_pid]
    if segment_pv1 is not None:
        oru_message_segments.append(segment_pv1)
    oru_message_segments.append(segment_obr)
    oru_message_segments += segment_obx
    full_oru_message: str = "\r".join(oru_message_segments)
    logger.debug("Generated ORU message", extra={"oru_message": full_oru_message})
    return full_oru_message


def _generate_msh_segment(msg_ctrl_id: Optional[str] = None) -> str:
    logger.debug("Generating MSH segment")
    trustomer_config: Dict = trustomer.get_trustomer_config()
    receiving_application = _hl7_escape(
        trustomer_config["hl7_config"]["outgoing_receiving_application"]
    )
    receiving_facility = _hl7_escape(
        trustomer_config["hl7_config"]["outgoing_receiving_facility"]
    )
    processing_id = _hl7_escape(
        trustomer_config["hl7_config"]["outgoing_processing_id"]
    )
    sending_application = _hl7_escape(
        trustomer_config["hl7_config"]["outgoing_sending_application"]
    )
    sending_facility = _hl7_escape(
        trustomer_config["hl7_config"]["outgoing_sending_facility"]
    )

    hl7_datetime = Hl7Wrapper.generate_hl7_datetime_now()
    if not msg_ctrl_id:
        msg_ctrl_id = Hl7Wrapper.generate_message_control_id()
    msh_segment: str = (
        f"MSH|^~\\&|{sending_application}|{sending_facility}|"
        f"{receiving_application}|{receiving_facility}|{hl7_datetime}||ORU^R01^ORU_R01|"
        f"{msg_ctrl_id}|{processing_id}|2.6"
    )
    logger.debug("Generated MSH segment", extra={"msh_segment": msh_segment})
    return msh_segment


def _generate_pid_segment(patient: Dict) -> str:
    logger.debug("Generating PID segment")
    patient_uuid = _hl7_escape(patient["uuid"])
    patient_mrn = _hl7_escape(patient.get("hospital_number", ""))
    patient_nhs = _hl7_escape(patient.get("nhs_number", ""))
    patient_identifier_list = []
    if patient_mrn:
        patient_identifier_list.append(f"{patient_mrn}^^^^MRN")
    if patient_nhs:
        patient_identifier_list.append(f"{patient_nhs}^^^^NHS")
    patient_identifiers = "~".join(patient_identifier_list)
    patient_name = (
        f"{_hl7_escape(patient['last_name'])}^{_hl7_escape(patient['first_name'])}"
    )
    dob_date = parse_iso8601_to_date(patient["dob"])
    patient_dob = "" if dob_date is None else dob_date.strftime("%Y%m%d")
    patient_sex = parse_sct_to_sex(patient["sex"])
    pid_segment: str = f"PID|1|{patient_uuid}|{patient_identifiers}||{patient_name}||{patient_dob}|{patient_sex}"
    logger.debug("Generated PID segment", extra={"pid_segment": pid_segment})
    return pid_segment


def _generate_pv1_segment(encounter: Dict) -> Union[str, None]:
    logger.debug("Generating PV1 segment")
    epr_encounter_id: Optional[str] = encounter.get("epr_encounter_id")
    if epr_encounter_id is None:
        return None
    escaped_epr_id = _hl7_escape(epr_encounter_id)
    location_ods_code: str = encounter[
        "location_ods_code"
    ]  # Don't escape this because it's a field
    admission_date: str = Hl7Wrapper.iso8601_to_hl7_datetime(encounter["admitted_at"])
    pv1_segment: str = f"PV1|1||{location_ods_code}||||||||||||||||{escaped_epr_id}|||||||||||||||||||||||||{admission_date}"
    logger.debug("Generated PV1 segment", extra={"pv1_segment": pv1_segment})
    return pv1_segment


def _generate_obr_segment(obs_set: Dict, collector: str = None) -> str:
    logger.debug("Generating OBR segment")
    collector_field = collector if collector else ""
    filler_order_number = _hl7_escape(obs_set["uuid"])
    obs_set_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_set["record_time"])
    obr_segment: str = f"OBR|1||{filler_order_number}|EWS|||{obs_set_datetime}|||{collector_field}|||||||||||||||F"
    logger.debug("Generated OBR segment", extra={"obr_segment": obr_segment})
    return obr_segment


def _generate_obx_segment(
    idx: int,
    obs_category: str,
    obs_code: str,
    obs_value: str,
    obs_datetime: str,
    obs_unit: Optional[str] = None,
    collector: Optional[str] = None,
    reference_range: Optional[str] = None,
    abnormal_flags: Optional[str] = None,
    patient_refused: Optional[bool] = False,
) -> str:
    # obs_category is one of the following: https://corepointhealth.com/resource-center/hl7-resources/hl7-data-types/
    obs_unit_field = f"^{obs_unit}" if obs_unit else ""
    collector_field = f"||{collector}" if collector else ""
    reference_range_field = reference_range or ""
    abnormal_flags_field = abnormal_flags or ""
    if patient_refused:
        obs_value = "patient_refused"
    return (
        f"OBX|{idx}|{obs_category}|{obs_code}||{obs_value}|{obs_unit_field}"
        f"|{reference_range_field}|{abnormal_flags_field}|||F|||{obs_datetime}{collector_field}"
    )


def _hl7_escape(unescaped: Optional[str]) -> str:
    if unescaped is None:
        return ""
    return (
        unescaped.replace("\\", "\\E\\")
        .replace("|", "\\F\\")
        .replace("~", "\\R\\")
        .replace("^", "\\S\\")
        .replace("&", "\\T\\")
    )


def _float_or_none_to_str(obs_value: Optional[str]) -> str:
    return str(round(float(obs_value))) if obs_value else ""


def _get_obs_with_value(observations: List[Dict], obs_type: str) -> Optional[Dict]:
    obs = next((o for o in observations if o["observation_type"] == obs_type), None)
    if obs is None:
        # No obs found with that name.
        return None
    if (
        obs["observation_value"] is None
        and obs["observation_string"] is None
        and obs["patient_refused"] is False
    ):
        # There is no value in the observation, so we don't care about it.
        return None
    return obs


def _generate_obx_hr(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for heart rate")
    segments: List[str] = []
    obs_hr: Optional[Dict] = _get_obs_with_value(obs_list, obs_type="heart_rate")
    if obs_hr is not None:
        obs_hr_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_hr["measured_time"])
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="HR",
                obs_value=_float_or_none_to_str(obs_hr["observation_value"]),
                obs_unit=_hl7_escape(obs_hr["observation_unit"]),
                obs_datetime=obs_hr_datetime,
                collector=collector,
                patient_refused=obs_hr["patient_refused"],
            )
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx + 1,
                obs_category="NM",
                obs_code="HRScore",
                obs_value=obs_hr["score_value"],
                obs_datetime=obs_hr_datetime,
            )
        )
    logger.debug(
        "Generated OBX segments for heart rate", extra={"obx_segments": segments}
    )
    return segments


def _generate_obx_rr(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for respiratory rate")
    segments: List[str] = []
    obs_rr: Optional[Dict] = _get_obs_with_value(obs_list, obs_type="respiratory_rate")
    if obs_rr is not None:
        obs_rr_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_rr["measured_time"])
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="RR",
                obs_value=_float_or_none_to_str(obs_rr["observation_value"]),
                obs_unit=_hl7_escape(obs_rr["observation_unit"]),
                obs_datetime=obs_rr_datetime,
                collector=collector,
                patient_refused=obs_rr["patient_refused"],
            )
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx + 1,
                obs_category="NM",
                obs_code="RRScore",
                obs_value=obs_rr["score_value"],
                obs_datetime=obs_rr_datetime,
            )
        )
    logger.debug(
        "Generated OBX segments for respiratory rate", extra={"obx_segments": segments}
    )
    return segments


def _generate_obx_dbp(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for diastolic blood pressure")
    segments: List[str] = []
    obs_dbp: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="diastolic_blood_pressure"
    )
    if obs_dbp is not None:
        obs_dbp_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_dbp["measured_time"])
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="DBP",
                obs_value=_float_or_none_to_str(obs_dbp["observation_value"]),
                obs_unit=_hl7_escape(obs_dbp["observation_unit"]),
                obs_datetime=obs_dbp_datetime,
                collector=collector,
                patient_refused=obs_dbp["patient_refused"],
            )
        )
        if obs_dbp.get("score_value", None) is not None:
            segments.append(
                _generate_obx_segment(
                    idx=start_idx + 1,
                    obs_category="NM",
                    obs_code="DBPScore",
                    obs_value=obs_dbp["score_value"],
                    obs_datetime=obs_dbp_datetime,
                )
            )
    logger.debug(
        "Generated OBX segments for diastolic blood pressure",
        extra={"obx_segments": segments},
    )
    return segments


def _generate_obx_sbp(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for systolic blood pressure")
    segments: List[str] = []
    obs_sbp: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="systolic_blood_pressure"
    )
    if obs_sbp is not None:
        obs_sbp_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_sbp["measured_time"])
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="SBP",
                obs_value=_float_or_none_to_str(obs_sbp["observation_value"]),
                obs_unit=_hl7_escape(obs_sbp["observation_unit"]),
                obs_datetime=obs_sbp_datetime,
                collector=collector,
                patient_refused=obs_sbp["patient_refused"],
            )
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx + 1,
                obs_category="NM",
                obs_code="SBPScore",
                obs_value=obs_sbp["score_value"],
                obs_datetime=obs_sbp_datetime,
            )
        )
    logger.debug(
        "Generated OBX segments for systolic blood pressure",
        extra={"obx_segments": segments},
    )
    return segments


def _generate_obx_bp_posture(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for bp posture")
    segments: List[str] = []

    # Get the position from either SBP or DBP obs metadata.
    obs_sbp: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="systolic_blood_pressure"
    )
    obs_dbp: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="diastolic_blood_pressure"
    )
    if (
        obs_sbp is not None
        and obs_sbp.get("observation_metadata")
        and obs_sbp["observation_metadata"].get("patient_position")
    ):
        position_value = obs_sbp["observation_metadata"]["patient_position"]
        position_datetime_iso = obs_sbp["measured_time"]
    elif (
        obs_dbp is not None
        and obs_dbp.get("observation_metadata")
        and obs_dbp["observation_metadata"].get("patient_position")
    ):
        position_value = obs_dbp["observation_metadata"]["patient_position"]
        position_datetime_iso = obs_dbp["measured_time"]
    else:
        position_value = None
        position_datetime_iso = None
    if position_value is not None:
        position_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(position_datetime_iso)
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="ST",
                obs_code="BPPOS",
                obs_value=_hl7_escape(position_value),
                obs_datetime=position_datetime,
                collector=collector,
            )
        )
    logger.debug(
        "Generated OBX segments for bp posture", extra={"obx_segments": segments}
    )
    return segments


def _generate_obx_spo2(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for oxygen saturation")
    segments: List[str] = []
    obs_spo2: Optional[Dict] = _get_obs_with_value(obs_list, obs_type="spo2")
    if obs_spo2 is not None:
        obs_spo2_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(
            obs_spo2["measured_time"]
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="SPO2",
                obs_value=_float_or_none_to_str(obs_spo2["observation_value"]),
                obs_unit=_hl7_escape(obs_spo2["observation_unit"]),
                obs_datetime=obs_spo2_datetime,
                collector=collector,
                patient_refused=obs_spo2["patient_refused"],
            )
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx + 1,
                obs_category="NM",
                obs_code="SPO2Score",
                obs_value=obs_spo2["score_value"],
                obs_datetime=obs_spo2_datetime,
            )
        )
    logger.debug(
        "Generated OBX segments for oxygen saturation", extra={"obx_segments": segments}
    )
    return segments


def _generate_obx_o2_therapy(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for oxygen therapy")
    segments: List[str] = []
    obs_o2_therapy: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="o2_therapy_status"
    )
    if obs_o2_therapy is not None:
        obs_o2_therapy_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(
            obs_o2_therapy["measured_time"]
        )

        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="O2Rate",
                obs_value=obs_o2_therapy["observation_value"],
                obs_unit=_hl7_escape(obs_o2_therapy["observation_unit"]),
                obs_datetime=obs_o2_therapy_datetime,
                collector=collector,
            )
        )
        start_idx += 1
        mask_code, mask_name = _get_o2_mask_type(obs_o2_therapy)

        if mask_code is not None:
            segments.append(
                _generate_obx_segment(
                    idx=start_idx,
                    obs_category="CE",
                    obs_code="O2Delivery",
                    obs_value=f"{_hl7_escape(mask_code)}^{_hl7_escape(mask_name)}",
                    obs_datetime=obs_o2_therapy_datetime,
                    collector=collector,
                )
            )
            start_idx += 1
        if obs_o2_therapy.get("score_value", None) is not None:
            segments.append(
                _generate_obx_segment(
                    idx=start_idx,
                    obs_category="NM",
                    obs_code="O2Score",
                    obs_value=obs_o2_therapy["score_value"],
                    obs_datetime=obs_o2_therapy_datetime,
                )
            )
    logger.debug(
        "Generated OBX segments for oxygen therapy", extra={"obx_segments": segments}
    )
    return segments


def _get_o2_mask_type(
    obs_o2_therapy: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    observation_metadata: Optional[Dict] = obs_o2_therapy.get("observation_metadata")
    if observation_metadata is None:
        return None, None

    mask_name = observation_metadata.get("mask")
    if not mask_name:
        return None, None

    trustomer_config: Dict = trustomer.get_trustomer_config()
    oxygen_masks = trustomer_config["send_config"]["oxygen_masks"]
    mask_code = None
    mask_pct = obs_o2_therapy["observation_metadata"].get("mask_percent", None)

    for mapping in oxygen_masks:
        if mapping["name"] == mask_name:
            mask_code = mapping["code"].replace(
                "{mask_percent}", str("21" if mask_pct is None else mask_pct)
            )
            break

    if mask_pct is not None:
        mask_name += f" {mask_pct}%"

    return mask_code, mask_name


def _generate_obx_temp(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for temperature")
    segments: List[str] = []
    obs_temp: Optional[Dict] = _get_obs_with_value(obs_list, obs_type="temperature")
    if obs_temp is not None:
        obs_temp_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(
            obs_temp["measured_time"]
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="NM",
                obs_code="TEMP",
                obs_value=obs_temp["observation_value"],
                obs_unit=_hl7_escape(obs_temp["observation_unit"]),
                obs_datetime=obs_temp_datetime,
                collector=collector,
                patient_refused=obs_temp["patient_refused"],
            )
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx + 1,
                obs_category="NM",
                obs_code="TEMPScore",
                obs_value=obs_temp["score_value"],
                obs_datetime=obs_temp_datetime,
            )
        )
    logger.debug(
        "Generated OBX segments for temperature", extra={"obx_segments": segments}
    )
    return segments


def _generate_obx_acvpu(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for ACVPU")
    segments: List[str] = []
    obs_acvpu: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="consciousness_acvpu"
    )
    if obs_acvpu is not None:
        obs_acvpu_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(
            obs_acvpu["measured_time"]
        )
        acvpu_value = _hl7_escape(obs_acvpu["observation_string"])
        segments.append(
            _generate_obx_segment(
                idx=start_idx,
                obs_category="CE",
                obs_code="ACVPU",
                obs_value=f"{acvpu_value[0]}^{acvpu_value}",
                obs_datetime=obs_acvpu_datetime,
                collector=collector,
            )
        )
        segments.append(
            _generate_obx_segment(
                idx=start_idx + 1,
                obs_category="NM",
                obs_code="ACVPUScore",
                obs_value=obs_acvpu["score_value"],
                obs_datetime=obs_acvpu_datetime,
            )
        )
    logger.debug("Generated OBX segments for ACVPU", extra={"obx_segments": segments})
    return segments


def _generate_obx_gcs(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for GCS")
    segments: List[str] = []
    obs_gcs: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="consciousness_gcs"
    )

    if obs_gcs is None:
        logger.debug("No GCS in observation set, no OBX segments to include")
        return []

    obs_gcs_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_gcs["measured_time"])

    current_obx_index: int = start_idx
    meta: Optional[Dict] = obs_gcs.get("observation_metadata")
    if meta is not None:
        # Loop through the following metadata keys for GCS, and add an OBX segment if they exist.
        logger.debug("Adding OBX segments for GCS metadata", extra={"metadata": meta})
        for meta_code, meta_obs_value, meta_obs_description in [
            ("GCS-Eyes", meta.get("gcs_eyes"), meta.get("gcs_eyes_description")),
            ("GCS-Verbal", meta.get("gcs_verbal"), meta.get("gcs_verbal_description")),
            ("GCS-Motor", meta.get("gcs_motor"), meta.get("gcs_motor_description")),
        ]:
            if meta_obs_value is None or meta_obs_description in [None, ""]:
                logger.info(
                    "Skipping OBX segment '%s', missing required metadata", meta_code
                )
                continue
            obs_value_field: str = (
                f"{meta_obs_value}^{_hl7_escape(meta_obs_description)}"
            )
            segments.append(
                _generate_obx_segment(
                    idx=current_obx_index,
                    obs_category="CE",
                    obs_code=meta_code,
                    obs_value=obs_value_field,
                    obs_datetime=obs_gcs_datetime,
                    collector=collector,
                )
            )
            current_obx_index += 1

    # Finally, add the overall GCS OBX segment.
    try:
        obs_value = str(int(float(obs_gcs["observation_value"])))
    except ValueError:
        obs_value = obs_gcs["observation_value"]
    segments.append(
        _generate_obx_segment(
            idx=current_obx_index,
            obs_category="NM",
            obs_code="GCS",
            obs_value=obs_value,
            obs_datetime=obs_gcs_datetime,
            collector=collector,
        )
    )
    logger.debug("Generated OBX segments for GCS", extra={"obx_segments": segments})
    return segments


def _generate_obx_nurse_concern(
    obs_list: List[Dict], collector: Optional[str], start_idx: int
) -> List[str]:
    logger.debug("Generating OBX segments for nurse concern")
    segments: List[str] = []
    obs_nurse_concern: Optional[Dict] = _get_obs_with_value(
        obs_list, obs_type="nurse_concern"
    )
    if obs_nurse_concern is not None:
        obs_nurse_concern_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(
            obs_nurse_concern["measured_time"]
        )
        nurse_concern_list: List[str] = obs_nurse_concern["observation_string"].split(
            ","
        )

        for idx, nurse_concern in enumerate(nurse_concern_list):
            nurse_concern_value: str = _hl7_escape(nurse_concern.strip())

            segments.append(
                _generate_obx_segment(
                    idx=start_idx + idx,
                    obs_category="ST",
                    obs_code="NC",
                    obs_value=nurse_concern_value,
                    obs_datetime=obs_nurse_concern_datetime,
                    collector=collector,
                )
            )
        logger.debug(
            "Generated OBX segments for Nurse concern", extra={"obx_segments": segments}
        )
    return segments


def _generate_obx_overall_score(obs_set: Dict, start_idx: int) -> List[str]:
    logger.debug("Generating OBX segments for overall score")
    segments: List[str] = []
    obs_set_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_set["record_time"])
    current_idx: int = start_idx

    # OBX ScoreSystem
    if obs_set.get("score_system"):
        if obs_set["score_system"].upper() in VALID_EWS_SCORE_SYSTEMS:
            scoring_system = obs_set["score_system"].upper()
        else:
            raise ValueError(f"Unexpected score system '{obs_set['score_system']}'")
        segments.append(
            _generate_obx_segment(
                idx=current_idx,
                obs_category="ST",
                obs_code="ScoringSystem",
                obs_value=_hl7_escape(scoring_system),
                obs_datetime=obs_set_datetime,
            )
        )
        current_idx += 1

    # OBX SpO2Scale
    if obs_set.get("score_system", "").upper() == "NEWS2" and obs_set.get("spo2_scale"):
        spo2_scale = f"Scale {obs_set['spo2_scale']}"
        segments.append(
            _generate_obx_segment(
                idx=current_idx,
                obs_category="ST",
                obs_code="SpO2Scale",
                obs_value=_hl7_escape(spo2_scale),
                obs_datetime=obs_set_datetime,
            )
        )
        current_idx += 1

    # OBX TotalScore
    if obs_set.get("score_value") is not None:
        reference_range: Optional[str] = obs_set.get("obx_reference_range")
        abnormal_flags: Optional[str] = obs_set.get("obx_abnormal_flags")
        segments.append(
            _generate_obx_segment(
                idx=current_idx,
                obs_category="NM",
                obs_code="TotalScore",
                obs_value=obs_set["score_value"],
                obs_datetime=obs_set_datetime,
                reference_range=_hl7_escape(reference_range),
                abnormal_flags=_hl7_escape(abnormal_flags),
            )
        )
        current_idx += 1

    # OBX Severity
    if obs_set.get("score_severity"):
        segments.append(
            _generate_obx_segment(
                idx=current_idx,
                obs_category="ST",
                obs_code="Severity",
                obs_value=obs_set["score_severity"],
                obs_datetime=obs_set_datetime,
            )
        )

    logger.debug(
        "Generated OBX segments for overall score", extra={"obx_segments": segments}
    )

    return segments


def _generate_obx_time_next_due(obs_set: Dict, start_idx: int) -> List[str]:

    logger.debug("Generating OBX segments for time nex obs set due")
    current_idx: int = start_idx
    obs_set_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_set["record_time"])
    segments: List[str] = []

    if obs_set.get("time_next_obs_set_due"):
        time_next_obs_set_due = Hl7Wrapper.iso8601_to_hl7_datetime(
            obs_set["time_next_obs_set_due"]
        )
        segments.append(
            _generate_obx_segment(
                idx=current_idx,
                obs_category="TS",
                obs_code="TimeNextObsSetDue",
                obs_value=time_next_obs_set_due,
                obs_datetime=obs_set_datetime,
            )
        )

    logger.debug(
        "Generated OBX segments for time nex obs set due",
        extra={"obx_segments": segments},
    )
    return segments


def _generate_obx_mins_late(obs_set: Dict, start_idx: int) -> List[str]:

    logger.debug("Generating OBX segments for minutes late")
    current_idx: int = start_idx
    obs_set_datetime = Hl7Wrapper.iso8601_to_hl7_datetime(obs_set["record_time"])
    segments: List[str] = []

    if obs_set.get("mins_late"):
        segments.append(
            _generate_obx_segment(
                idx=current_idx,
                obs_category="NM",
                obs_code="MinutesLate",
                obs_value=obs_set["mins_late"],
                obs_datetime=obs_set_datetime,
            )
        )

    logger.debug(
        "Generated OBX segments for time nex obs set due",
        extra={"obx_segments": segments},
    )
    return segments
