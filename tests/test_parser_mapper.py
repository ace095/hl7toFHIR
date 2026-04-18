import pytest

from app.mapper import map_to_fhir_bundle
from app.parser import HL7ParseError, parse_hl7_message


ADT_MESSAGE = (
    "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
    "PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M\r"
    "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
)


def test_parse_hl7_message_extracts_required_segments() -> None:
    segments = parse_hl7_message(ADT_MESSAGE)
    assert {"MSH", "PID", "PV1"}.issubset(segments.keys())


def test_map_to_fhir_bundle_creates_patient_and_encounter() -> None:
    bundle = map_to_fhir_bundle(parse_hl7_message(ADT_MESSAGE))
    assert bundle["resourceType"] == "Bundle"
    assert len(bundle["entry"]) == 2
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][1]["resource"]["resourceType"] == "Encounter"


def test_parse_hl7_message_requires_pid() -> None:
    message = "MSH|^~\\&|A|B|C|D|202401011200||ADT^A01|1|P|2.5"
    with pytest.raises(HL7ParseError, match="PID"):
        parse_hl7_message(message)
