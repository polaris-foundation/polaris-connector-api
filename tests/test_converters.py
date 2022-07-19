import draymed

from dhos_connector_api.helpers.converters import parse_sct_to_sex


def test_parse_sct_to_sex() -> None:
    result = parse_sct_to_sex(draymed.codes.code_from_name("male", "sex"))
    assert result == "1"


def test_parse_sct_to_sex_unknown() -> None:
    result = parse_sct_to_sex("blarg")
    assert result == "3"
