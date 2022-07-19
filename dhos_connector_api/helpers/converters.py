from typing import Optional

import draymed
from she_logging import logger

# LHS is the name of the sex, RHS is list of possible ways EPR might have of referring to that sex.
EPR_SEX_MAP = {
    "male": ["1", "M"],
    "female": ["2", "F"],
    "unknown": ["3", "U"],
    "indeterminate": ["4", "I"],
}


def parse_sex_to_sct(raw_sex: Optional[str]) -> str:
    if raw_sex is None:
        raw_sex = ""
    else:
        raw_sex = raw_sex.upper()

    sex_name = next((k for k, v in EPR_SEX_MAP.items() if raw_sex in v), None)
    if sex_name is None:
        logger.info("Unknown sex code: %s", raw_sex)
        sex_name = "unknown"
    return draymed.codes.code_from_name(sex_name, "sex")


def parse_sct_to_sex(sex_sct: str) -> str:
    sex_name: str = "unknown"

    if sex_sct:
        try:
            sex_name = draymed.codes.description_from_code(sex_sct, "sex")
        except KeyError:
            logger.debug("Couldn't determine sex from sct code '%s'", sex_sct)

    # Draymed descriptions are in sentence case (e.g. Male, Female, Indeterminate, Unknown).
    raw_sex = EPR_SEX_MAP.get(sex_name.lower())
    if raw_sex is None:
        logger.info("Unknown sex SCT code %s", sex_sct)
        raw_sex = EPR_SEX_MAP["unknown"]
    # Prefer the first (numeric) value for the named sex.
    return raw_sex[0]
