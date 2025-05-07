import pytest
from src.services.fhir_conversion_service import FHIRConversionService
from src.schemas.clinical_note import (
    ClinicalNoteResponse,
    Patient,
    Condition,
    Medication,
)


def test_convert_to_fhir():
    """Test converting clinical note data to FHIR format."""
    # Create test data
    patient = Patient(
        name="John Doe",
        id="123",
        gender="Male",
        dob="1980-05-01",
    )

    conditions = [
        Condition(
            text="Type 2 Diabetes Mellitus",
            code="E11.9",
            notes="Patient has been managing well with diet and exercise",
        )
    ]

    medications = [
        Medication(
            text="Metformin 500mg",
            code="6809",
            dosage="500 mg",
            route="PO",
            frequency="BID",
            instructions="Take with meals",
        )
    ]

    clinical_note = ClinicalNoteResponse(
        patient=patient, conditions=conditions, medications=medications
    )

    # Convert to FHIR
    fhir_service = FHIRConversionService()
    fhir_resources = fhir_service.convert_to_fhir(clinical_note)

    # Verify patient resource
    patient_resource = fhir_resources["patient"]
    assert patient_resource["resourceType"] == "Patient"
    assert patient_resource["id"] == "123"
    assert patient_resource["name"][0]["text"] == "John Doe"
    assert patient_resource["gender"] == "male"
    assert patient_resource["birthDate"] == "1980-05-01"

    # Verify condition resource
    assert len(fhir_resources["conditions"]) == 1
    condition = fhir_resources["conditions"][0]
    assert condition["resourceType"] == "Condition"
    assert condition["code"]["text"] == "Type 2 Diabetes Mellitus"
    assert condition["code"]["coding"][0]["code"] == "E11.9"
    assert (
        condition["code"]["coding"][0]["system"] == "http://hl7.org/fhir/sid/icd-10-cm"
    )
    assert condition["clinicalStatus"]["coding"][0]["code"] == "active"
    assert condition["verificationStatus"]["coding"][0]["code"] == "confirmed"
    assert condition["subject"]["reference"] == "Patient/123"
    assert (
        condition["note"][0]["text"]
        == "Patient has been managing well with diet and exercise"
    )

    # Verify medication resource
    assert len(fhir_resources["medications"]) == 1
    medication = fhir_resources["medications"][0]
    assert medication["resourceType"] == "MedicationStatement"
    assert medication["status"] == "active"
    assert medication["medicationCodeableConcept"]["text"] == "Metformin 500mg"
    assert medication["medicationCodeableConcept"]["coding"][0]["code"] == "6809"
    assert (
        medication["medicationCodeableConcept"]["coding"][0]["system"]
        == "http://www.nlm.nih.gov/research/umls/rxnorm"
    )
    assert medication["subject"]["reference"] == "Patient/123"
    assert (
        medication["dosage"][0]["text"] == "Dosage: 500 mg | Route: PO | Frequency: BID"
    )
    assert medication["dosage"][0]["route"]["text"] == "PO"
    assert medication["dosage"][0]["timing"]["code"]["text"] == "BID"
    assert medication["note"][0]["text"] == "Take with meals"


def test_convert_to_fhir_with_missing_data():
    """Test converting clinical note data with missing fields to FHIR format."""
    # Create test data with missing fields
    patient = Patient(name=None, id=None, gender=None, dob=None, additional_info={})

    conditions = [Condition(text="Hypertension", code=None, notes="")]

    medications = [
        Medication(
            text="Lisinopril",
            code=None,
            dosage=None,
            route=None,
            frequency=None,
            instructions=None,
        )
    ]

    clinical_note = ClinicalNoteResponse(
        patient=patient, conditions=conditions, medications=medications
    )

    # Convert to FHIR
    fhir_service = FHIRConversionService()
    fhir_resources = fhir_service.convert_to_fhir(clinical_note)

    # Verify patient resource with missing data
    patient_resource = fhir_resources["patient"]
    assert patient_resource["resourceType"] == "Patient"
    assert patient_resource["id"] == "unknown"
    assert patient_resource["gender"] == "unknown"
    assert "birthDate" not in patient_resource

    # Verify condition resource with missing code
    assert len(fhir_resources["conditions"]) == 1
    condition = fhir_resources["conditions"][0]
    assert condition["code"]["text"] == "Hypertension"
    assert condition["code"]["coding"] == []
    assert "note" not in condition

    # Verify medication resource with missing details
    assert len(fhir_resources["medications"]) == 1
    medication = fhir_resources["medications"][0]
    assert medication["medicationCodeableConcept"]["text"] == "Lisinopril"
    assert medication["medicationCodeableConcept"]["coding"] == []
    assert "dosage" not in medication
    assert "note" not in medication


def test_convert_to_fhir_with_dob():
    """Test converting clinical note data with date of birth to FHIR format."""
    # Create test data with DOB
    patient = Patient(
        name="Jane Smith",
        id="456",
        gender="Female",
        dob="1990-07-15",
    )

    conditions = [
        Condition(
            text="Hypertension",
            code="I10",
            notes="Mild hypertension, well controlled",
        )
    ]

    medications = [
        Medication(
            text="Lisinopril 10mg",
            code="29046",
            dosage="10 mg",
            route="PO",
            frequency="daily",
            instructions="Take in the morning",
        )
    ]

    clinical_note = ClinicalNoteResponse(
        patient=patient, conditions=conditions, medications=medications
    )

    # Convert to FHIR
    fhir_service = FHIRConversionService()
    fhir_resources = fhir_service.convert_to_fhir(clinical_note)

    # Verify patient resource with DOB
    patient_resource = fhir_resources["patient"]
    assert patient_resource["resourceType"] == "Patient"
    assert patient_resource["id"] == "456"
    assert patient_resource["name"][0]["text"] == "Jane Smith"
    assert patient_resource["gender"] == "female"
    assert patient_resource["birthDate"] == "1990-07-15"

    # Verify condition resource
    assert len(fhir_resources["conditions"]) == 1
    condition = fhir_resources["conditions"][0]
    assert condition["code"]["text"] == "Hypertension"
    assert condition["code"]["coding"][0]["code"] == "I10"
    assert condition["note"][0]["text"] == "Mild hypertension, well controlled"

    # Verify medication resource
    assert len(fhir_resources["medications"]) == 1
    medication = fhir_resources["medications"][0]
    assert medication["medicationCodeableConcept"]["text"] == "Lisinopril 10mg"
    assert medication["medicationCodeableConcept"]["coding"][0]["code"] == "29046"
    assert (
        medication["dosage"][0]["text"]
        == "Dosage: 10 mg | Route: PO | Frequency: daily"
    )
    assert medication["note"][0]["text"] == "Take in the morning"


def test_convert_to_fhir_with_hyperlipidemia():
    """Test converting clinical note data with hyperlipidemia and related conditions to FHIR format."""
    # Create test data
    patient = Patient(
        name=None,
        id="patient--001",
        gender=None,
        dob=None,
    )

    conditions = [
        Condition(
            text="Hyperlipidemia",
            code="E78.5",
            notes="",
        ),
        Condition(
            text="Overweight status, decreased HDL",
            code=None,
            notes="No exact match found",
        ),
    ]

    medications = [
        Medication(
            text="atorvastatin tab 20 mg PO daily qHS",
            code="617310",
            dosage="20 mg",
            route="PO",
            frequency="QD",
            instructions="Initiate; 1 tablet daily at bedtime",
        ),
        Medication(
            text="metformin 500mg tab",
            code="861007",
            dosage="500 mg",
            route="PO",
            frequency="QD",
            instructions="1 tablet daily at bedtime",
        ),
    ]

    clinical_note = ClinicalNoteResponse(
        patient=patient, conditions=conditions, medications=medications
    )

    # Convert to FHIR
    fhir_service = FHIRConversionService()
    fhir_resources = fhir_service.convert_to_fhir(clinical_note)

    # Verify patient resource
    assert fhir_resources["patient"]["resourceType"] == "Patient"
    assert fhir_resources["patient"]["id"] == "patient--001"
    assert fhir_resources["patient"]["gender"] == "unknown"

    # Verify condition resources
    assert len(fhir_resources["conditions"]) == 2

    # First condition (Hyperlipidemia)
    condition1 = fhir_resources["conditions"][0]
    assert condition1["resourceType"] == "Condition"
    assert condition1["code"]["text"] == "Hyperlipidemia"
    assert condition1["code"]["coding"][0]["code"] == "E78.5"
    assert condition1["clinicalStatus"]["coding"][0]["code"] == "active"
    assert condition1["verificationStatus"]["coding"][0]["code"] == "confirmed"
    assert condition1["subject"]["reference"] == "Patient/patient--001"

    # Second condition (Overweight status)
    condition2 = fhir_resources["conditions"][1]
    assert condition2["code"]["text"] == "Overweight status, decreased HDL"
    assert condition2["code"]["coding"] == []
    assert condition2["note"][0]["text"] == "No exact match found"

    # Verify medication resources
    assert len(fhir_resources["medications"]) == 2

    # First medication (atorvastatin)
    medication1 = fhir_resources["medications"][0]
    assert medication1["resourceType"] == "MedicationStatement"
    assert medication1["status"] == "active"
    assert (
        medication1["medicationCodeableConcept"]["text"]
        == "atorvastatin tab 20 mg PO daily qHS"
    )
    assert medication1["medicationCodeableConcept"]["coding"][0]["code"] in [
        "617310",
        "597966",
    ]
    assert medication1["subject"]["reference"] == "Patient/patient--001"
    assert (
        medication1["dosage"][0]["text"] == "Dosage: 20 mg | Route: PO | Frequency: QD"
    )
    assert medication1["dosage"][0]["route"]["text"] == "PO"
    assert medication1["dosage"][0]["timing"]["code"]["text"] == "QD"
    assert medication1["note"][0]["text"] == "Initiate; 1 tablet daily at bedtime"

    # Second medication (metformin)
    medication2 = fhir_resources["medications"][1]
    assert medication2["medicationCodeableConcept"]["text"] == "metformin 500mg tab"
    assert medication2["medicationCodeableConcept"]["coding"][0]["code"] == "861007"
    assert (
        medication2["dosage"][0]["text"] == "Dosage: 500 mg | Route: PO | Frequency: QD"
    )
    assert medication2["note"][0]["text"] == "1 tablet daily at bedtime"
