from __future__ import annotations

import re
from typing import Dict, List


class HL7ParseError(ValueError):
    """Raised when an HL7 message cannot be parsed."""


def _safe_field(fields: List[str], index: int) -> str:
    return fields[index] if index < len(fields) else ""


def parse_hl7_message(hl7_message: str) -> Dict[str, List[str]]:
    lines = [line.strip() for line in re.split(r"[\r\n]+", hl7_message.strip()) if line.strip()]
    if not lines:
        raise HL7ParseError("HL7 message is empty.")

    segments: Dict[str, List[str]] = {}
    for line in lines:
        fields = line.split("|")
        segment = fields[0].upper() if fields else ""
        if not segment:
            continue
        if segment not in segments:
            segments[segment] = fields

    if "MSH" not in segments:
        raise HL7ParseError("HL7 message must contain an MSH segment.")
    if "PID" not in segments:
        raise HL7ParseError("HL7 message must contain a PID segment.")

    msh = segments["MSH"]
    message_type = _safe_field(msh, 8)
    if message_type and not message_type.startswith("ADT"):
        raise HL7ParseError(f"Unsupported HL7 message type '{message_type}'. Only ADT is supported.")

    return segments
