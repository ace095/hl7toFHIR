import pytest

from app.mapper import map_to_fhir_bundle
from app.parser import HL7ParseError, parse_hl7_message


ADT_MESSAGE = (
    "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
    "PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M\r"
    "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
)


def test_parse_hl7_message_extracts_required_segments() -> None:
    segments, warnings = parse_hl7_message(ADT_MESSAGE)
    assert {"MSH", "PID", "PV1"}.issubset(segments.keys())


def test_map_to_fhir_bundle_creates_patient_and_encounter() -> None:
    segments, warnings = parse_hl7_message(ADT_MESSAGE)
    bundle = map_to_fhir_bundle(segments, warnings)
    assert bundle["resourceType"] == "Bundle"
    assert len(bundle["entry"]) == 2
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][1]["resource"]["resourceType"] == "Encounter"
    # Verify deterministic identifier: {assigning_authority}|{id_type}|{id}
    patient = bundle["entry"][0]["resource"]
    assert patient["id"] == "HOSP|MR|123456"
    assert patient["identifier"][0]["value"] == "123456"
    assert patient["identifier"][0]["type"]["code"] == "MR"


def test_parse_hl7_message_requires_pid() -> None:
    message = "MSH|^~\\&|A|B|C|D|202401011200||ADT^A01|1|P|2.5"
    with pytest.raises(HL7ParseError, match="PID"):
        parse_hl7_message(message)


# ============================================================================
# R7: Robust test coverage for edge cases and non-sunny scenarios
# ============================================================================


def test_repeated_segments_emit_warning() -> None:
    """S6: Repeated PID segments should be detected and warned."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||111^^^HOSP^MR||DOE^JOHN||19800101|M\r"
        "PID|2||222^^^HOSP^MR||SMITH^JANE||19890202|F\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )
    segments, warnings = parse_hl7_message(message)
    assert any("Repeated segment" in w for w in warnings), "Should warn about repeated PID"
    # MVP uses first instance only
    assert segments["PID"][3] == "111^^^HOSP^MR"


def test_missing_pv1_returns_patient_only() -> None:
    """S5: ADT without PV1 should return bundle with Patient only."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M"
    )
    segments, warnings = parse_hl7_message(message)
    bundle = map_to_fhir_bundle(segments, warnings)
    assert bundle["resourceType"] == "Bundle"
    assert len(bundle["entry"]) == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"


def test_missing_assigning_authority_emits_warning() -> None:
    """S7-like: Patient ID without assigning authority should warn about ambiguity."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||12345^^^||DOE^JOHN||19800101|M\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )
    segments, warnings = parse_hl7_message(message)
    warnings_from_mapper: list[str] = []
    bundle = map_to_fhir_bundle(segments, warnings_from_mapper)
    assert any("assigning authority" in w.lower() for w in warnings_from_mapper), \
        "Should warn about missing assigning authority"
    # ID should default to 'unknown' for assigning authority
    patient = bundle["entry"][0]["resource"]
    assert "unknown|" in patient["id"]


def test_multiple_identifiers_in_pid3_emits_warning() -> None:
    """S7: Multiple identifiers (repetitions) in PID-3 should warn."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||A123^^^HOSP^MR~B999^^^ALT^MR||DOE^JOHN||19800101|M\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )
    segments, warnings = parse_hl7_message(message)
    warnings_from_mapper: list[str] = []
    bundle = map_to_fhir_bundle(segments, warnings_from_mapper)
    assert any("multiple identifier" in w.lower() for w in warnings_from_mapper), \
        "Should warn about repeated identifiers"
    # Should use first identifier only
    patient = bundle["entry"][0]["resource"]
    assert patient["id"] == "HOSP|MR|A123"
    assert patient["identifier"][0]["value"] == "A123"


def test_unknown_gender_code_maps_to_unknown() -> None:
    """S9: Unknown gender codes should map to 'unknown'."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|X\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )
    segments, warnings = parse_hl7_message(message)
    bundle = map_to_fhir_bundle(segments, warnings)
    patient = bundle["entry"][0]["resource"]
    assert patient["gender"] == "unknown"


def test_invalid_birth_date_omitted_silently() -> None:
    """S8: Invalid birth date format should be omitted from Patient (no birthDate field)."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||123456^^^HOSP^MR||DOE^JOHN||19801340|M\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )
    segments, warnings = parse_hl7_message(message)
    bundle = map_to_fhir_bundle(segments, warnings)
    patient = bundle["entry"][0]["resource"]
    assert "birthDate" not in patient, "Invalid birthDate should not be included"


def test_valid_birth_date_included() -> None:
    """Birth date in valid YYYYMMDD format should be normalized to YYYY-MM-DD."""
    message = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M\r"
        "PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345"
    )
    segments, warnings = parse_hl7_message(message)
    bundle = map_to_fhir_bundle(segments, warnings)
    patient = bundle["entry"][0]["resource"]
    assert patient["birthDate"] == "1980-01-01"


def test_deterministic_identifier_prevents_collisions() -> None:
    """Identifiers from different facilities should produce different IDs."""
    msg_facility_a = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||12345^^^HOSP_A^MR||DOE^JOHN||19800101|M"
    )
    msg_facility_b = (
        "MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r"
        "PID|1||12345^^^HOSP_B^MR||DOE^JOHN||19800101|M"
    )
    
    segments_a, _ = parse_hl7_message(msg_facility_a)
    bundle_a = map_to_fhir_bundle(segments_a, [])
    patient_a = bundle_a["entry"][0]["resource"]
    
    segments_b, _ = parse_hl7_message(msg_facility_b)
    bundle_b = map_to_fhir_bundle(segments_b, [])
    patient_b = bundle_b["entry"][0]["resource"]
    
    # Same MR number but different facilities => different IDs
    assert patient_a["id"] == "HOSP_A|MR|12345"
    assert patient_b["id"] == "HOSP_B|MR|12345"
    assert patient_a["id"] != patient_b["id"], "Identifiers should be scoped by facility"
