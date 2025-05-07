from typing import Dict, List, Any, Tuple
from src.schemas.clinical_note import (
    ClinicalNoteResponse,
    Patient,
    Condition,
    Medication,
)
import json
import logging
from fhir.resources.patient import Patient as FHIRPatient
from fhir.resources.condition import Condition as FHIRCondition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.humanname import HumanName
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.dosage import Dosage
from fhir.resources.timing import Timing
from fhir.resources.codeableconcept import CodeableConcept as TimingCodeableConcept
from fhir.resources.annotation import Annotation
from fhir.resources.codeablereference import CodeableReference
from dataclasses import dataclass
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    WARNING = auto()
    ERROR = auto()


@dataclass
class ValidationIssue:
    """Represents a validation issue found during quality checking."""

    severity: ValidationSeverity
    resource_type: str
    field: str
    message: str


class FHIRConversionService:
    """Service for converting clinical note data to FHIR format."""

    def convert_to_fhir(self, clinical_note: ClinicalNoteResponse) -> Dict[str, Any]:
        """Convert clinical note data to FHIR format.

        Args:
            clinical_note: The structured clinical note data

        Returns:
            Dictionary containing FHIR resources and validation issues
        """
        try:
            # Create FHIR resources
            fhir_patient = self._create_patient_resource(clinical_note.patient)
            fhir_conditions = [
                self._create_condition_resource(condition, clinical_note.patient)
                for condition in clinical_note.conditions
            ]
            fhir_medications = [
                self._create_medication_resource(medication, clinical_note.patient)
                for medication in clinical_note.medications
            ]

            # Validate resources
            validation_issues = self._validate_resources(
                fhir_patient, fhir_conditions, fhir_medications
            )

            # Convert to dictionary format for API response
            return {
                "patient": self._serialize_patient(fhir_patient),
                "conditions": [c.dict(exclude_none=True) for c in fhir_conditions],
                "medications": [
                    self._serialize_medication(m) for m in fhir_medications
                ],
                "validation_issues": [
                    {
                        "severity": issue.severity.name,
                        "resource_type": issue.resource_type,
                        "field": issue.field,
                        "message": issue.message,
                    }
                    for issue in validation_issues
                ],
            }

        except Exception as e:
            logger.error(f"Error converting to FHIR format: {str(e)}")
            raise

    def _validate_resources(
        self,
        patient: FHIRPatient,
        conditions: List[FHIRCondition],
        medications: List[MedicationStatement],
    ) -> List[ValidationIssue]:
        """Validate FHIR resources for quality and completeness.

        Args:
            patient: The FHIR Patient resource
            conditions: List of FHIR Condition resources
            medications: List of FHIR MedicationStatement resources

        Returns:
            List of validation issues found
        """
        issues = []

        # Validate patient
        if not patient.name:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    resource_type="Patient",
                    field="name",
                    message="Patient name is missing. This may affect record matching.",
                )
            )
        if not patient.birthDate:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    resource_type="Patient",
                    field="birthDate",
                    message="Patient date of birth is missing. This may affect age-based calculations.",
                )
            )
        if not patient.gender or patient.gender == "unknown":
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    resource_type="Patient",
                    field="gender",
                    message="Patient gender is missing or unknown. This may affect clinical decision support.",
                )
            )

        # Validate conditions
        for i, condition in enumerate(conditions):
            if not condition.code.coding:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        resource_type="Condition",
                        field="code",
                        message=f"Condition '{condition.code.text}' is missing an ICD-10 code. This may affect billing and analytics.",
                    )
                )

        # Validate medications
        for i, medication in enumerate(medications):
            if not medication.medication.concept.coding:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        resource_type="MedicationStatement",
                        field="medication",
                        message=f"Medication '{medication.medication.concept.text}' is missing an RxNorm code. This may affect drug interaction checking.",
                    )
                )
            if not medication.dosage:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        resource_type="MedicationStatement",
                        field="dosage",
                        message=f"Medication '{medication.medication.concept.text}' is missing dosage information. This may affect medication safety checks.",
                    )
                )

        # Log validation issues
        for issue in issues:
            if issue.severity == ValidationSeverity.ERROR:
                logger.error(f"Validation error: {issue.message}")
            else:
                logger.warning(f"Validation warning: {issue.message}")

        return issues

    def _serialize_patient(self, patient: FHIRPatient) -> Dict[str, Any]:
        """Serialize patient resource to dictionary format."""
        data = patient.dict(exclude_none=True)
        # Convert birthDate to string if present
        if "birthDate" in data:
            data["birthDate"] = str(data["birthDate"])
        return data

    def _serialize_medication(self, medication: MedicationStatement) -> Dict[str, Any]:
        """Serialize medication statement to dictionary format."""
        data = medication.dict(exclude_none=True)
        # Add medicationCodeableConcept for backward compatibility
        if "medication" in data and "concept" in data["medication"]:
            data["medicationCodeableConcept"] = data["medication"]["concept"]
        return data

    def _create_patient_resource(self, patient: Patient) -> FHIRPatient:
        """Create a FHIR Patient resource."""
        fhir_patient = FHIRPatient(
            id=patient.id or "unknown",
            gender=patient.gender.lower() if patient.gender else "unknown",
        )

        if patient.dob:
            fhir_patient.birthDate = patient.dob

        if patient.name:
            name_parts = patient.name.split()
            name = HumanName(
                text=patient.name,
                family=name_parts[-1] if name_parts else None,
                given=name_parts[:-1] if len(name_parts) > 1 else None,
            )
            fhir_patient.name = [name]

        return fhir_patient

    def _create_condition_resource(
        self, condition: Condition, patient: Patient
    ) -> FHIRCondition:
        """Create a FHIR Condition resource."""
        fhir_condition = FHIRCondition(
            code=CodeableConcept(
                text=condition.text,
                coding=(
                    [
                        Coding(
                            code=condition.code,
                            system="http://hl7.org/fhir/sid/icd-10-cm",
                        )
                    ]
                    if condition.code
                    else []
                ),
            ),
            clinicalStatus=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                        code="active",
                    )
                ]
            ),
            verificationStatus=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        code="confirmed",
                    )
                ]
            ),
            subject=Reference(reference=f"Patient/{patient.id or 'unknown'}"),
        )

        if condition.notes:
            fhir_condition.note = [Annotation(text=condition.notes)]

        return fhir_condition

    def _create_medication_resource(
        self, medication: Medication, patient: Patient
    ) -> MedicationStatement:
        """Create a FHIR MedicationStatement resource."""
        # Create the medication concept
        medication_concept = CodeableConcept(
            text=medication.text,
            coding=(
                [
                    Coding(
                        code=medication.code,
                        system="http://www.nlm.nih.gov/research/umls/rxnorm",
                    )
                ]
                if medication.code
                else []
            ),
        )

        # Create the medication reference
        medication_reference = CodeableReference(concept=medication_concept)

        # Create the medication statement
        fhir_medication = MedicationStatement(
            status="active",
            medication=medication_reference,
            subject=Reference(reference=f"Patient/{patient.id or 'unknown'}"),
        )

        # Add dosage information if available
        if any([medication.dosage, medication.route, medication.frequency]):
            dosage = Dosage(
                text=self._format_dosage_text(medication),
            )

            if medication.route:
                dosage.route = CodeableConcept(text=medication.route)

            if medication.frequency:
                dosage.timing = Timing(
                    code=TimingCodeableConcept(text=medication.frequency)
                )

            fhir_medication.dosage = [dosage]

        # Add instructions if available
        if medication.instructions:
            fhir_medication.note = [Annotation(text=medication.instructions)]

        return fhir_medication

    def _format_dosage_text(self, medication: Medication) -> str:
        """Format medication dosage information into a readable string."""
        parts = []
        if medication.dosage:
            parts.append(f"Dosage: {medication.dosage}")
        if medication.route:
            parts.append(f"Route: {medication.route}")
        if medication.frequency:
            parts.append(f"Frequency: {medication.frequency}")
        return " | ".join(parts) if parts else None
