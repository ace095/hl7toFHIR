from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Dict, List, Optional
from urllib.parse import quote
from app.vocabulary import map_admission_class, map_gender


def _safe_field(fields: List[str], index: int) -> str:
    return fields[index] if index < len(fields) else ""


def _first_component(value: str) -> str:
    return value.split("^", 1)[0] if value else ""


def _normalize_birth_date(raw: str) -> Optional[str]:
    if not raw:
        return None
    date_part = raw[:8]
    try:
        return datetime.strptime(date_part, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _map_gender_with_warning(raw: str, warnings: List[str]) -> str:
    fhir_gender, display, is_mapped = map_gender(raw)
    if not is_mapped and raw and raw.upper() not in ("M", "F", "O", "U"):
        warnings.append(
            f"Patient gender code '{raw}' is not mapped to standard FHIR value; "
            f"using '{fhir_gender}' for Patient.gender."
        )
    return fhir_gender


def _map_adt_trigger_to_encounter_status(trigger_event: str) -> str:
    """
    Map HL7 ADT trigger events (MSH-9.2) to FHIR Encounter.status.
    
    Risk mitigation: Trigger events encode clinical workflow state (admit, transfer, discharge).
    Mapping to correct Encounter.status ensures downstream systems understand encounter lifecycle.
    
    FHIR Encounter.status: planned | arrived | in-progress | onleave | finished | cancelled
    HL7 ADT Trigger Events:
      - A01 (Admit): in-progress (patient now in active encounter)
      - A02 (Transfer): in-progress (encounter continues, location changes)
      - A03 (Discharge): finished (encounter has ended)
      - A04 (Register): arrived (pre-encounter registration)
      - A05 (Pre-admit): planned (scheduled but not yet active)
      - A06 (Change outpatient to inpatient): in-progress (escalation)
      - A07 (Change inpatient to outpatient): finished (de-escalation, encounter ends)
      - A08 (Update patient info): in-progress (operational update, no status change)
      - A11 (Cancel admit): cancelled (admit was reversed)
      - A12 (Cancel transfer): cancelled (transfer was reversed)
      - A13 (Cancel discharge): in-progress (discharge was reversed, patient still admitted)
    """
    mapping = {
        # Admit/Start
        "A01": "in-progress",  # Admit
        "A02": "in-progress",  # Transfer
        # Discharge/End
        "A03": "finished",     # Discharge
        "A07": "finished",     # Change inpatient to outpatient (de-escalation, encounter ends)
        # Pre-encounter states
        "A04": "arrived",      # Register (pre-encounter)
        "A05": "planned",      # Pre-admit (future encounter)
        # State transitions
        "A06": "in-progress",  # Change outpatient to inpatient (escalation)
        "A08": "in-progress",  # Update patient info (no status change)
        # Cancellations
        "A11": "cancelled",    # Cancel admit
        "A12": "cancelled",    # Cancel transfer
        "A13": "in-progress",  # Cancel discharge (reverses discharge, back to in-progress)
    }
    # Default to in-progress for unknown ADT types
    return mapping.get(trigger_event, "in-progress") if trigger_event else "in-progress"


def _is_numeric_oid(value: str) -> bool:
    parts = value.split(".")
    return len(parts) > 1 and all(part.isdigit() for part in parts)


def _identifier_system(assigning_authority: str) -> str:
    if _is_numeric_oid(assigning_authority):
        return f"urn:oid:{assigning_authority}"
    return f"https://hl7tofhir.local/namingsystem/{quote(assigning_authority, safe='')}"


def _fhir_safe_id(prefix: str, composite_identifier: str) -> str:
    # 24 hex chars = 96 bits of SHA-256 output; deterministic, within FHIR id length limits,
    # and with negligible collision probability for expected MVP identifier volumes.
    identifier_hash = hashlib.sha256(composite_identifier.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{identifier_hash}"


def _parse_cx_identifier(raw: str) -> dict:
    """
    Parse an HL7 CX (composite ID) field: ID^Check Digit^Check Digit Scheme^Assigning Authority^Identifier Type
    Returns dict with 'id', 'assigning_authority', 'id_type' extracted.
    
    Decision: Build deterministic, collision-safe identifiers using:
      identifier.system = OID URN only for numeric OIDs; otherwise a URL NamingSystem namespace
      identifier.value = "{assigning_authority}|{id_type}|{id}"
    
    Risk mitigation: Assigning authority is critical for cross-facility safety.
    If missing, emit a warning since identifier may be ambiguous.
    
    Note: PID-3 can have repetitions (ID1~ID2~...). We take the first one per MVP scope.
    """
    # Split on repetition character first (MVP handles first repetition only)
    first_repetition = raw.split("~")[0] if raw else ""
    
    components = first_repetition.split("^") if first_repetition else []
    
    id_value = components[0] if len(components) > 0 else ""
    assigning_authority = components[3] if len(components) > 3 else ""
    id_type = components[4] if len(components) > 4 else "MR"  # MR (Medical Record) is typical default
    
    return {
        "id": id_value,
        "assigning_authority": assigning_authority,
        "id_type": id_type,
    }


def map_to_fhir_bundle(segments: Dict[str, List[str]], warnings: List[str]) -> Dict[str, object]:
    pid = segments["PID"]
    pv1 = segments.get("PV1")
    msh = segments["MSH"]
    
    # Extract ADT trigger event from MSH-9.2 (format: MESSAGE_TYPE^TRIGGER_EVENT^MESSAGE_STRUCTURE)
    msh9_raw = _safe_field(msh, 8)
    msh9_components = msh9_raw.split("^") if msh9_raw else []
    trigger_event = msh9_components[1] if len(msh9_components) > 1 else ""

    # Parse Patient Identifier (PID-3) with deterministic collision-safe logic
    pid3_raw = _safe_field(pid, 3)
    pid3 = _parse_cx_identifier(pid3_raw)
    
    # Check for multiple identifier repetitions (MVP handles first only)
    if "~" in pid3_raw:
        warnings.append(
            f"Patient identifier PID-3 contains multiple identifier repetitions; "
            f"only first identifier '{pid3['id']}' will be processed."
        )
    
    # Build composite identity scoped by assigning authority + identifier type for cross-facility safety
    patient_id_value = pid3["id"] or "unknown"
    patient_assigning_authority = pid3["assigning_authority"]
    patient_id_type = pid3["id_type"]
    
    if not patient_assigning_authority:
        warnings.append(
            f"Patient identifier PID-3 missing assigning authority (facility/system); "
            f"identifier '{patient_id_value}' may be ambiguous across facilities."
        )
        patient_assigning_authority = "unknown"
    
    patient_identifier = f"{patient_assigning_authority}|{patient_id_type}|{patient_id_value}"
    patient_fhir_id = _fhir_safe_id("patient", patient_identifier)
    
    patient_name = _safe_field(pid, 5).split("^")
    family_name = patient_name[0] if patient_name else ""
    given_name = patient_name[1] if len(patient_name) > 1 else ""

    patient_resource: Dict[str, object] = {
        "resourceType": "Patient",
        "id": patient_fhir_id,
        "identifier": [
            {
                "system": _identifier_system(patient_assigning_authority),
                "type": {"code": patient_id_type},
                "value": patient_identifier,
            }
        ],
        "name": [{"family": family_name, "given": [given_name] if given_name else []}],
        "gender": _map_gender_with_warning(_safe_field(pid, 8), warnings),
    }

    birth_date = _normalize_birth_date(_safe_field(pid, 7))
    if birth_date:
        patient_resource["birthDate"] = birth_date

    entries: List[Dict[str, object]] = [{"resource": patient_resource}]

    if pv1:
        # PV1.19 is Visit Number (preferred for encounter identity per HL7 standard)
        # PV1.3 is Assigned Patient Location (fallback for lightweight ADT payloads)
        pv1_19_raw = _safe_field(pv1, 19)
        pv1_3_raw = _safe_field(pv1, 3)
        
        # Try to parse as CX if PV1.19 present, otherwise use PV1.3 location
        if pv1_19_raw:
            pv1_19 = _parse_cx_identifier(pv1_19_raw)
            encounter_id_value = pv1_19["id"]
            encounter_assigning_authority = pv1_19["assigning_authority"] or patient_assigning_authority
            if not encounter_id_value:
                encounter_id_value = _first_component(pv1_3_raw)
                warnings.append(
                    "Encounter visit number field PV1.19 is present but empty; "
                    "resolved encounter identifier from PV1.3 location component."
                )
                if not encounter_id_value:
                    encounter_id_value = "unknown"
        else:
            # Fallback: use location component from PV1.3 (first component)
            encounter_id_value = _first_component(pv1_3_raw)
            encounter_assigning_authority = patient_assigning_authority
            if not encounter_id_value:
                encounter_id_value = "unknown"
            warnings.append(
                "Encounter identifier resolved from PV1.3 location component (PV1.19 Visit Number absent); "
                "visit number is preferred for deterministic encounter identity."
            )
        
        encounter_identifier = f"{encounter_assigning_authority}|VN|{encounter_id_value}"
        encounter_fhir_id = _fhir_safe_id("encounter", encounter_identifier)
        
        # Map ADT trigger event to Encounter status per HL7 workflow semantics
        encounter_status = _map_adt_trigger_to_encounter_status(trigger_event)
        
        pv1_2_raw = _safe_field(pv1, 2) or "I"
        admission_class_code, admission_class_display, is_admission_mapped = map_admission_class(pv1_2_raw)
        if not is_admission_mapped and pv1_2_raw not in ("I", "O", "E", "U", "N", "P"):
            warnings.append(
                f"Admission class code '{pv1_2_raw}' is not mapped to standard FHIR value; "
                f"using '{admission_class_code}' for Encounter.class."
            )
        
        encounter_resource: Dict[str, object] = {
            "resourceType": "Encounter",
            "id": encounter_fhir_id,
            "status": encounter_status,
            "class": {"code": admission_class_code},
            "subject": {"reference": f"Patient/{patient_fhir_id}"},
            "identifier": [
                {
                    "system": _identifier_system(encounter_assigning_authority),
                    "type": {"code": "VN"},
                    "value": encounter_identifier,
                }
            ],
        }
        entries.append({"resource": encounter_resource})

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}
