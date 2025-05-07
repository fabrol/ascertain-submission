import pytest
import pytest_asyncio
import os
from src.services.clinical_note_agent import ClinicalNoteAgent
from src.schemas.clinical_note import (
    ClinicalNoteResponse,
    Patient,
    Condition,
    Medication,
)
from src.services.llm_service import LLMService
from src.services.medical_code_service import MedicalCodeService
from src.config import settings


@pytest.mark.integration
class TestClinicalNoteAgentE2E:
    """End-to-end tests for the ClinicalNoteAgent."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup(self):
        """Setup test environment."""
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
            )

    @pytest.mark.asyncio
    async def test_process_real_clinical_note(self):
        """Test processing a real clinical note end-to-end."""
        # Arrange
        agent = ClinicalNoteAgent()
        test_note = """
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

        # Act
        result = await agent.process_clinical_note(test_note)

        print(f"Result: {result}")

        # Assert
        assert isinstance(result, ClinicalNoteResponse)
        assert result.error is None

        # Verify conditions
        assert len(result.conditions) >= 1
        hyperlipidemia = next(
            c for c in result.conditions if "hyperlipidemia" in c.text.lower()
        )
        assert "E78.5" in hyperlipidemia.code  # Should have found an ICD-10 code
        assert "hyperlipidemia" in hyperlipidemia.text.lower()

        # Verify medications
        assert len(result.medications) >= 2
        atorvastatin = next(
            m for m in result.medications if "atorvastatin" in m.text.lower()
        )
        assert "20 mg" in atorvastatin.dosage
        assert "qHS" in atorvastatin.frequency
        assert atorvastatin.code in [
            "617310",
            "597966",
        ]  # Should have found an RxNorm code

        metformin = next(m for m in result.medications if "metformin" in m.text.lower())
        assert "500 mg" in metformin.dosage
        assert "daily" in metformin.frequency
        assert metformin.code is not None  # Should have found an RxNorm code


'''
    @pytest.mark.asyncio
    async def test_process_note_with_unknown_conditions(self):
        """Test processing a note with conditions that might not have exact codes."""
        # Arrange
        agent = ClinicalNoteAgent()
        test_note = """
        ASSESSMENT:
        1. Mild upper respiratory infection
        2. Chronic fatigue syndrome
        
        PLAN:
        1. Rest and fluids
        2. Follow-up in 2 weeks
        """

        # Act
        result = await agent.process_clinical_note(test_note)

        # Assert
        assert isinstance(result, ClinicalNoteResponse)
        assert result.error is None
        assert len(result.conditions) >= 2

        # Verify that even if exact codes aren't found, we still get the conditions
        uri = next(c for c in result.conditions if "respiratory" in c.text.lower())
        assert "respiratory" in uri.text.lower()

        cfs = next(c for c in result.conditions if "fatigue" in c.text.lower())
        assert "fatigue" in cfs.text.lower()

    @pytest.mark.asyncio
    async def test_process_note_with_complex_medications(self):
        """Test processing a note with complex medication instructions."""
        # Arrange
        agent = ClinicalNoteAgent()
        test_note = """
        PLAN:
        1. Start lisinopril 10mg PO daily, increase to 20mg after 1 week if BP > 140/90
        2. Take aspirin 81mg PO daily with food
        3. Use albuterol inhaler 2 puffs Q4H PRN for wheezing
        """

        # Act
        result = await agent.process_clinical_note(test_note)

        # Assert
        assert isinstance(result, ClinicalNoteResponse)
        assert result.error is None
        assert len(result.medications) >= 3

        # Verify complex medication parsing
        lisinopril = next(
            m for m in result.medications if "lisinopril" in m.text.lower()
        )
        assert lisinopril.code is not None
        assert "10mg" in lisinopril.dosage
        assert "daily" in lisinopril.frequency

        aspirin = next(m for m in result.medications if "aspirin" in m.text.lower())
        assert aspirin.code is not None
        assert "81mg" in aspirin.dosage
        assert "with food" in aspirin.instructions

        albuterol = next(m for m in result.medications if "albuterol" in m.text.lower())
        assert albuterol.code is not None
        assert "Q4H" in albuterol.frequency
        assert "PRN" in albuterol.instructions

'''
