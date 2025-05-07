from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ClinicalNoteRequest(BaseModel):
    """Request containing clinical note text to analyze."""

    note_text: str


class Patient(BaseModel):
    """Patient information extracted from clinical note."""

    name: Optional[str] = None
    id: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[str] = None  # Date of Birth as a top-level field
    additional_info: Dict[str, Any] = {}


class Condition(BaseModel):
    """Medical condition extracted from clinical note."""

    text: str
    code: Optional[str] = None
    notes: str = ""
    confidence: Optional[float] = None


class Medication(BaseModel):
    """Medication extracted from clinical note."""

    text: str
    code: Optional[str] = None
    dosage: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    instructions: Optional[str] = None
    confidence: Optional[float] = None


class ClinicalNoteResponse(BaseModel):
    """Response containing extracted information from clinical note."""

    patient: Patient
    conditions: List[Condition]
    medications: List[Medication]
    error: Optional[str] = None

    def __str__(self) -> str:
        """Return a pretty-printed string representation of the clinical note response."""
        lines = []

        # Add patient information
        lines.append("Patient Information:")
        if self.patient.name:
            lines.append(f"  Name: {self.patient.name}")
        if self.patient.id:
            lines.append(f"  ID: {self.patient.id}")
        if self.patient.age:
            lines.append(f"  Age: {self.patient.age}")
        if self.patient.gender:
            lines.append(f"  Gender: {self.patient.gender}")
        if self.patient.dob:
            lines.append(f"  DOB: {self.patient.dob}")
        if self.patient.additional_info:
            lines.append("  Additional Info:")
            for key, value in self.patient.additional_info.items():
                lines.append(f"    {key}: {value}")

        # Add conditions
        if self.conditions:
            lines.append("\nConditions:")
            for condition in self.conditions:
                lines.append(f"  - {condition.text}")
                if condition.code:
                    lines.append(f"    Code: {condition.code}")
                if condition.notes:
                    lines.append(f"    Notes: {condition.notes}")
                if condition.confidence is not None:
                    lines.append(f"    Confidence: {condition.confidence:.2f}")

        # Add medications
        if self.medications:
            lines.append("\nMedications:")
            for med in self.medications:
                lines.append(f"  - {med.text}")
                if med.code:
                    lines.append(f"    Code: {med.code}")
                if med.dosage:
                    lines.append(f"    Dosage: {med.dosage}")
                if med.route:
                    lines.append(f"    Route: {med.route}")
                if med.frequency:
                    lines.append(f"    Frequency: {med.frequency}")
                if med.instructions:
                    lines.append(f"    Instructions: {med.instructions}")
                if med.confidence is not None:
                    lines.append(f"    Confidence: {med.confidence:.2f}")

        # Add error if present
        if self.error:
            lines.append(f"\nError: {self.error}")

        return "\n".join(lines)
