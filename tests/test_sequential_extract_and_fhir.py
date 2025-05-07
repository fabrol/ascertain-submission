import pytest
from fastapi.testclient import TestClient
from src.schemas.clinical_note import ClinicalNoteRequest


def test_sequential_extract_and_fhir_conversion(client: TestClient):
    """Test the complete sequential process from clinical note to FHIR resources."""
    # Sample clinical note
    note_text = """
    SOAP Note - Encounter Date: 2024-03-15 (Follow-Up Visit)
    Patient: patient--001
    S: Pt returns for follow-up on cholesterol, as planned in prior physical. Labs drawn on previous encounter indicating elevated LDL (165 mg/dL), mildly reduced HDL (38 mg/dL), triglycerides at upper normal limits (145 mg/dL). Pt admits difficulty adhering strictly to suggested dietary changes, but did slightly increase physical activity. Denies chest discomfort, palpitations, SOB, orthopnea, or PND.

    O:
    Vitals today:

    BP: 134/84 mmHg
    HR: 78 bpm
    Weight stable at 192 lbs
    Physical Exam unchanged from last assessment, no new findings.

    Review of labs (drawn on 2023-10-26):

    LDL cholesterol elevated at 165 mg/dL (desirable <100 mg/dL)
    HDL low at 38 mg/dL (desired >40 mg/dL)
    Triglycerides borderline at 145 mg/dL (normal <150 mg/dL)
    No indications of DM, liver or kidney dysfunction observed on CMP results.

    A:

    Hyperlipidemia
    Overweight status, decreased HDL
    Stable vitals, no acute distress or cardiovascular symptoms
    P:

    Initiate atorvastatin 20 mg PO daily qHS; discussed risks/benefits with pt
    Pt advised again regarding diet and lifestyle modifications
    Recommend continued aerobic exercise (at least 4 sessions/week, moderate intensity, 30-40 mins per session)
    Repeat lipid panel, LFTs after 3 months of statin therapy initiation
    Return for follow-up in 3 months or earlier if any adverse reaction occurs.
    Prescription Note:

    Atorvastatin 20mg tab Disp: #90 (ninety) tabs Sig: 1 tablet PO daily at bedtime Refills: 3
    Metformin 500mg tab Disp: #90 (ninety) tabs Sig: 1 tablet PO daily at bedtime Refills: 3
    Signed:
    Dr. Mark Reynolds, MD
    Internal Medicine
    """

    # Step 1: Extract structured data
    extract_response = client.post("/extract-structured", json={"note_text": note_text})
    assert extract_response.status_code == 200
    structured_data = extract_response.json()

    # Step 2: Convert to FHIR
    fhir_response = client.post("/to_fhir", json=structured_data)
    assert fhir_response.status_code == 200
    fhir_resources = fhir_response.json()

    # Verify the complete FHIR bundle structure
    assert "patient" in fhir_resources
    assert "conditions" in fhir_resources
    assert "medications" in fhir_resources

    # Verify patient resource
    assert fhir_resources["patient"]["resourceType"] == "Patient"
    assert fhir_resources["patient"]["id"] == "patient--001"

    # Verify conditions
    assert len(fhir_resources["conditions"]) >= 1
    conditions = {c["code"]["text"].lower(): c for c in fhir_resources["conditions"]}

    assert "hyperlipidemia" in conditions
    hyperlipidemia = conditions["hyperlipidemia"]
    assert hyperlipidemia["code"]["coding"][0]["code"] == "E78.5"
    assert hyperlipidemia["clinicalStatus"]["coding"][0]["code"] == "active"
    assert hyperlipidemia["verificationStatus"]["coding"][0]["code"] == "confirmed"

    # Verify medications
    assert len(fhir_resources["medications"]) >= 2
    medications = {
        m["medicationCodeableConcept"]["text"].lower(): m
        for m in fhir_resources["medications"]
    }
    print(fhir_resources["medications"])

    # Helper function to check medication properties
    def verify_medication(
        med_name: str,
        expected_dosage: str,
        expected_route: str,
        expected_frequency: str,
    ):
        assert any(
            med_name.lower() in key.lower() for key in medications.keys()
        ), f"Medication {med_name} not found in response"
        med = next(
            m
            for m in medications.values()
            if med_name.lower() in m["medicationCodeableConcept"]["text"].lower()
        )

        # Verify basic structure
        assert med["resourceType"] == "MedicationStatement"
        assert med["status"] == "active"
        assert "medication" in med
        assert "concept" in med["medication"]
        assert "coding" in med["medication"]["concept"]
        assert len(med["medication"]["concept"]["coding"]) > 0
        assert (
            med["medication"]["concept"]["coding"][0]["system"]
            == "http://www.nlm.nih.gov/research/umls/rxnorm"
        )

        # Verify dosage information
        assert "dosage" in med
        assert len(med["dosage"]) > 0
        dosage = med["dosage"][0]

        # Check dosage text contains expected components
        dosage_text = dosage["text"].lower()
        assert (
            expected_dosage.lower() in dosage_text
        ), f"Expected dosage {expected_dosage} not found in {dosage_text}"
        assert (
            expected_route.lower() in dosage_text
        ), f"Expected route {expected_route} not found in {dosage_text}"
        assert (
            expected_frequency.lower() in dosage_text
        ), f"Expected frequency {expected_frequency} not found in {dosage_text}"

        # Verify timing and route if present
        if "timing" in dosage:
            assert "code" in dosage["timing"]
            assert "text" in dosage["timing"]["code"]
            assert (
                expected_frequency.lower() in dosage["timing"]["code"]["text"].lower()
            )

        if "route" in dosage:
            assert "text" in dosage["route"]
            assert expected_route.lower() in dosage["route"]["text"].lower()

    # Verify atorvastatin
    verify_medication(
        med_name="atorvastatin",
        expected_dosage="20 mg",
        expected_route="po",
        expected_frequency="qHS",
    )

    # Verify metformin
    verify_medication(
        med_name="metformin",
        expected_dosage="500 mg",
        expected_route="po",
        expected_frequency="daily",
    )


def test_sequential_process_with_invalid_note(client: TestClient):
    """Test the sequential process with an invalid note."""
    # Step 1: Try to extract structured data from invalid note
    extract_response = client.post(
        "/extract-structured", json={"note_text": ""}  # Empty note
    )
    assert (
        extract_response.status_code == 200
    )  # Should still return 200 with empty data

    structured_data = extract_response.json()

    # Step 2: Convert to FHIR
    fhir_response = client.post("/to_fhir", json=structured_data)
    assert fhir_response.status_code == 200

    fhir_resources = fhir_response.json()

    # Verify empty FHIR resources
    assert fhir_resources["patient"]["id"] == "unknown"
    assert fhir_resources["patient"]["gender"] == "unknown"
    assert fhir_resources["conditions"] == []
    assert fhir_resources["medications"] == []
