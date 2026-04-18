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


def map_to_fhir_bundle(segments: Dict[str, List[str]]) -> Dict[str, object]:
    pid = segments["PID"]
    pv1 = segments.get("PV1")

    patient_identifier = _first_component(_safe_field(pid, 3)) or "unknown"
    patient_name = _safe_field(pid, 5).split("^")
    family_name = patient_name[0] if patient_name else ""
    given_name = patient_name[1] if len(patient_name) > 1 else ""

    patient_resource: Dict[str, object] = {
        "resourceType": "Patient",
        "id": patient_identifier,
        "identifier": [{"value": patient_identifier}],
        "name": [{"family": family_name, "given": [given_name] if given_name else []}],
        "gender": _map_gender(_safe_field(pid, 8)),
    }

    birth_date = _normalize_birth_date(_safe_field(pid, 7))
    if birth_date:
        patient_resource["birthDate"] = birth_date

    entries: List[Dict[str, object]] = [{"resource": patient_resource}]

    if pv1:
        encounter_identifier = _first_component(_safe_field(pv1, 19)) or _first_component(_safe_field(pv1, 3))
        encounter_resource: Dict[str, object] = {
            "resourceType": "Encounter",
            "id": encounter_identifier or "encounter-1",
            "status": "in-progress",
            "class": {"code": _safe_field(pv1, 2) or "IMP"},
            "subject": {"reference": f"Patient/{patient_identifier}"},
        }
        if encounter_identifier:
            encounter_resource["identifier"] = [{"value": encounter_identifier}]
        entries.append({"resource": encounter_resource})

    return {"resourceType": "Bundle", "type": "collection", "entry": entries}
