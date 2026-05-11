import pytest

from app.vocabulary import VocabularyMapping, map_gender, map_admission_class


class TestVocabularyMapping:
    """Test vocabulary mapping framework."""
    
    def test_gender_mapping_male(self) -> None:
        """M should map to male."""
        fhir_code, display, is_mapped = map_gender("M")
        assert fhir_code == "male"
        assert is_mapped is True
    
    def test_gender_mapping_female(self) -> None:
        """F should map to female."""
        fhir_code, display, is_mapped = map_gender("F")
        assert fhir_code == "female"
        assert is_mapped is True
    
    def test_gender_mapping_other(self) -> None:
        """O should map to other."""
        fhir_code, display, is_mapped = map_gender("O")
        assert fhir_code == "other"
        assert is_mapped is True
    
    def test_gender_mapping_unknown(self) -> None:
        """U should map to unknown."""
        fhir_code, display, is_mapped = map_gender("U")
        assert fhir_code == "unknown"
        assert is_mapped is True
    
    def test_gender_mapping_ambiguous(self) -> None:
        """A (ambiguous) should map to other."""
        fhir_code, display, is_mapped = map_gender("A")
        assert fhir_code == "other"
        assert is_mapped is True
    
    def test_gender_mapping_unmapped(self) -> None:
        """Unknown gender code should return unmapped status."""
        fhir_code, display, is_mapped = map_gender("X")
        assert is_mapped is False
        # Should return the unmapped code as fallback
        assert "X" in display or "unknown" in fhir_code.lower()
    
    def test_gender_mapping_empty(self) -> None:
        """Empty gender should default to unknown."""
        fhir_code, display, is_mapped = map_gender("")
        assert fhir_code == "unknown"
        assert is_mapped is False
    
    def test_admission_class_inpatient(self) -> None:
        """I should map to inpatient (IMP)."""
        fhir_code, display, is_mapped = map_admission_class("I")
        assert fhir_code == "IMP"
        assert is_mapped is True
    
    def test_admission_class_outpatient(self) -> None:
        """O should map to ambulatory (AMB)."""
        fhir_code, display, is_mapped = map_admission_class("O")
        assert fhir_code == "AMB"
        assert is_mapped is True
    
    def test_admission_class_emergency(self) -> None:
        """E should map to emergency (EMER)."""
        fhir_code, display, is_mapped = map_admission_class("E")
        assert fhir_code == "EMER"
        assert is_mapped is True
    
    def test_admission_class_urgent_maps_to_inpatient(self) -> None:
        """U (urgent) should map to inpatient as fallback."""
        fhir_code, display, is_mapped = map_admission_class("U")
        assert fhir_code == "IMP"
        assert is_mapped is True
    
    def test_admission_class_unmapped(self) -> None:
        """Unknown admission class should return unmapped status."""
        fhir_code, display, is_mapped = map_admission_class("Z")
        assert is_mapped is False
    
    def test_vocabulary_mapping_case_insensitive(self) -> None:
        """Vocabulary mapping should be case-insensitive."""
        fhir_code_upper, _, is_mapped_upper = map_gender("M")
        fhir_code_lower, _, is_mapped_lower = map_gender("m")
        assert fhir_code_upper == fhir_code_lower
        assert is_mapped_upper is True
        assert is_mapped_lower is True
