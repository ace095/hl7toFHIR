"""
Vocabulary Mapping Framework

Maps HL7 v2 local codes to FHIR standard codes (value sets).
Preserves original codes for audit trail when exact mapping unavailable.

Each mapping has:
  - source_system: Source vocabulary identifier (e.g., "HL7-v2-gender", "local-admission-class")
  - local_code: The HL7 v2 code to map
  - fhir_code: The FHIR value set code to map to
  - fhir_display: Human-readable FHIR display value
  - comment: Reason for mapping (for audit/documentation)
"""

from typing import Dict, Optional


class VocabularyMapping:
    """Manages vocabulary code mappings from HL7 v2 to FHIR."""
    
    def __init__(self):
        # Dictionary keyed by (source_system, local_code) → (fhir_code, fhir_display)
        self.mappings: Dict[tuple, tuple] = {}
        self._load_default_mappings()
    
    def _load_default_mappings(self):
        """Load built-in mappings for common HL7 v2 vocabularies."""
        
        # Gender codes (HL7 v2 PID-8 to FHIR Patient.gender)
        gender_mappings = [
            ("HL7-gender", "M", "male", "Male"),
            ("HL7-gender", "F", "female", "Female"),
            ("HL7-gender", "O", "other", "Other"),
            ("HL7-gender", "U", "unknown", "Unknown"),
            ("HL7-gender", "A", "other", "Ambiguous (mapped to other)"),
            ("HL7-gender", "N", "unknown", "Not applicable (mapped to unknown)"),
        ]
        
        # Admission class codes (HL7 v2 PV1-2 to FHIR Encounter.class)
        # Note: FHIR Encounter.class uses v3/IHE codes
        admission_class_mappings = [
            ("HL7-admission-class", "I", "IMP", "Inpatient"),
            ("HL7-admission-class", "O", "AMB", "Outpatient/Ambulatory"),
            ("HL7-admission-class", "E", "EMER", "Emergency"),
            ("HL7-admission-class", "U", "IMP", "Urgent (mapped to inpatient)"),
            ("HL7-admission-class", "N", "IMP", "Not yet set (mapped to inpatient)"),
            ("HL7-admission-class", "P", "AMB", "Preadmit (mapped to ambulatory)"),
        ]
        
        # Load mappings into dictionary
        for system, local_code, fhir_code, display in gender_mappings + admission_class_mappings:
            self.mappings[(system, local_code)] = (fhir_code, display)
    
    def map_code(self, source_system: str, local_code: str, default: Optional[str] = None) -> tuple:
        """
        Map a local code to FHIR standard code.
        
        Args:
            source_system: Vocabulary source identifier
            local_code: The code to map
            default: Default FHIR code if mapping not found
        
        Returns:
            (fhir_code, fhir_display, is_mapped)
            - is_mapped: True if mapping found, False if using default
        """
        if not local_code:
            return (default or "unknown", "Unknown", False)
        
        key = (source_system, local_code.upper())
        if key in self.mappings:
            fhir_code, display = self.mappings[key]
            return (fhir_code, display, True)
        
        # No mapping found; return default
        return (default or local_code, f"Unmapped: {local_code}", False)
    
    def is_mapped(self, source_system: str, local_code: str) -> bool:
        """Check if a code has an explicit mapping."""
        return (source_system, local_code.upper()) in self.mappings


# Global instance
_vocab = VocabularyMapping()


def map_gender(local_code: str) -> tuple:
    """
    Map HL7 v2 gender code to FHIR gender.
    
    Returns:
        (fhir_gender, display, is_mapped)
    """
    return _vocab.map_code("HL7-gender", local_code, default="unknown")


def map_admission_class(local_code: str) -> tuple:
    """
    Map HL7 v2 admission class to FHIR encounter class.
    
    Returns:
        (fhir_class, display, is_mapped)
    """
    return _vocab.map_code("HL7-admission-class", local_code, default="IMP")
