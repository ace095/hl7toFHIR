from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional


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


def _map_gender(raw: str) -> str:
    mapping = {
        "M": "male",
        "F": "female",
        "O": "other",
        "U": "unknown",
    }
    return mapping.get(raw.upper(), "unknown") if raw else "unknown"


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


def _parse_cx_identifier(raw: str) -> dict:
    """
    Parse an HL7 CX (composite ID) field: ID^Check Digit^Check Digit Scheme^Assigning Authority^Identifier Type
    Returns dict with 'id', 'assigning_authority', 'id_type' extracted.
    
    Decision: Build deterministic, collision-safe identifiers using:
      system = "urn:oid:assigning_authority" or "urn:unknown" if missing
      value = "{id}|{id_type}" (scoped by assigning authority via system)
    
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
    
    # Build patient ID scoped by assigning authority + identifier type for cross-facility safety
    patient_id_value = pid3["id"] or "unknown"
    patient_assigning_authority = pid3["assigning_authority"]
    patient_id_type = pid3["id_type"]
    
    if not patient_assigning_authority:
        warnings.append(
            f"Patient identifier PID-3 missing assigning authority (facility/system); "
            f"identifier '{patient_id_value}' may be ambiguous across facilities."
        )
        patient_assigning_authority = "unknown"
    
    # Deterministic ID format: {assigning_authority}|{id_type}|{id}
    # This ensures "123" at Hospital A (HOSP_A|MR|123) != "123" at Hospital B (HOSP_B|MR|123)
    patient_identifier = f"{patient_assigning_authority}|{patient_id_type}|{patient_id_value}"
    
    patient_name = _safe_field(pid, 5).split("^")
    family_name = patient_name[0] if patient_name else ""
    given_name = patient_name[1] if len(patient_name) > 1 else ""

    patient_resource: Dict[str, object] = {
        "resourceType": "Patient",
        "id": patient_identifier,
        "identifier": [
            {
                "system": f"urn:oid:{patient_assigning_authority}",
                "type": {"code": patient_id_type},
                "value": patient_id_value,
            }
        ],
        "name": [{"family": family_name, "given": [given_name] if given_name else []}],
        "gender": _map_gender(_safe_field(pid, 8)),
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
        else:
            # Fallback: use location component from PV1.3 (first component)
            encounter_id_value = _first_component(pv1_3_raw)
            encounter_assigning_authority = patient_assigning_authority
            if not encounter_id_value:
                encounter_id_value = "encounter-unknown"
            warnings.append(
                "Encounter identifier resolved from PV1.3 location component (PV1.19 Visit Number absent); "
                "visit number is preferred for deterministic encounter identity."
            )
        
        # Deterministic Encounter ID using same pattern as Patient for consistency
        encounter_identifier = f"{encounter_assigning_authority}|VN|{encounter_id_value}"
        
        # Map ADT trigger event to Encounter status per HL7 workflow semantics
        encounter_status = _map_adt_trigger_to_encounter_status(trigger_event)
        
        encounter_resource: Dict[str, object] = {
            "resourceType": "Encounter",
            "id": encounter_identifier,
            "status": encounter_status,
            "class": {"code": _safe_field(pv1, 2) or "IMP"},
            "subject": {"reference": f"Patient/{patient_identifier}"},
            "identifier": [
                {
                    "system": f"urn:oid:{encounter_assigning_authority}",
                    "type": {"code": "VN"},
                    "value": encounter_id_value,
                }
            ],
        }
        entries.append({"resource": encounter_resource})

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}
