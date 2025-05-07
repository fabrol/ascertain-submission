from typing import List, Optional, Dict, Any
import logging
import json
from textwrap import dedent
from agents import Agent, function_tool, Runner
from sqlalchemy.orm import Session

from src.config import settings
from src.schemas.clinical_note import (
    Patient,
    Condition,
    Medication,
    ClinicalNoteResponse,
)
from src.services.medical_code_service import MedicalCodeService
from src.services.llm_service import LLMService


# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ClinicalNoteAgent:
    """
    Agent for processing clinical notes using OpenAI's Agent framework.
    Extracts structured data including patient info, conditions with ICD-10 codes,
    and medications with RxNorm codes.
    """

    # Current schema version - increment this when the response structure changes
    CURRENT_VERSION = "1.0.0"

    def __init__(
        self, db: Optional[Session] = None, llm_service: Optional[LLMService] = None
    ):
        """
        Initialize the clinical note agent.

        Args:
            db: Optional SQLAlchemy database session for caching
            llm_service: Optional LLM service instance to use
        """
        if not settings.is_openai_configured():
            raise ValueError(
                "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )

        self.db = db
        self.model = "gpt-4o"  # DO NOT CHANGE THIS MODEL
        self.llm_service = llm_service or LLMService(db=db)
        self.medical_code_service = MedicalCodeService(
            db=db, llm_service=self.llm_service
        )

        # Initialize the agent with tools
        self.agent = self._create_agent()

    async def _lookup_icd10(self, condition_text: str) -> Dict[str, Any]:
        """Look up the ICD-10 code for a medical condition.

        Args:
            condition_text: The medical condition to look up

        Returns:
            Dictionary containing code, description, notes, and confidence
        """
        result = await self.medical_code_service.lookup_icd10(condition_text)
        if not result:
            return {
                "code": None,
                "description": None,
                "notes": "No match found",
                "confidence": None,
            }

        return {
            "code": result.code,
            "description": result.description,
            "notes": "" if result.code else "No exact match found",
            "confidence": result.confidence,
        }

    async def _lookup_rxnorm(self, medication_text: str) -> Dict[str, Any]:
        """Look up the RxNorm code for a medication.

        Args:
            medication_text: The medication to look up

        Returns:
            Dictionary containing code, description, notes, and confidence
        """
        result = await self.medical_code_service.lookup_rxnorm(medication_text)
        if not result:
            return {
                "code": None,
                "description": None,
                "notes": "No match found",
                "confidence": None,
            }

        return {
            "code": result.code,
            "description": result.description,
            "notes": "" if result.code else "No exact match found",
            "confidence": result.confidence,
        }

    def _create_agent(self) -> Agent:
        """Create and configure the OpenAI Agent with necessary tools."""
        # Define the system prompt with detailed instructions
        system_prompt = dedent(
            """
            ==== INSTRUCTIONS ====

            You are a clinical‐information‐extraction agent. From a SOAP‐format medical note, you must extract and normalize:

            1. Patient Information  
               • Fields: name, id, age, gender, dob, additional_info  
               • If any are missing, set to null.

            2. Conditions  
               • Extract all formally diagnosed conditions (Assessment or elsewhere).  
               • For each, call the tool `lookup_icd10(condition_text)` to retrieve an ICD-10 code.  
               • If no match or ambiguous, set `"code": null` and note ambiguity in `"notes"`.

            3. Medications  
               • Extract all medications mentioned (Plan or elsewhere).  
               • Capture: entire text for medication, dosage, route, frequency, instructions.  
               • For frequency, prefer explicitly stated over inferred.
               • For each, call the tool `lookup_rxnorm(medication_text)` to retrieve an RxNorm code. Give it all the text for the medication.
               • If missing or ambiguous, set fields to null and explain in `"instructions"` or `"notes"`.

            ==== OUTPUT FORMAT ====
            You must return ONLY a raw JSON object with the following structure. Do not include any markdown formatting, code blocks, or explanatory text.

            {
              "patient": {
                "name": "string or null",
                "id": "string or null",
                "age": "string or null",
                "gender": "string (M, F, or null)",
                "dob": "string (YYYY-MM-DD) or null",
                "additional_info": {}
              },
              "conditions": [
                {
                  "text": "exact phrase from note",
                  "code": "ICD-10 code or null",
                  "notes": "string or blank"
                }
              ],
              "medications": [
                {
                  "text": "exact phrase from note",
                  "code": "RxNorm code or null",
                  "dosage": "string or null", // Amountunits
                  "route": "string or null",
                  "frequency": "string or null", // Normalize to standard medical frequencies (PRN, QD, daily, BID, TID, QID, Q4H, Q6H, Q8H, Q12H, Q24H)
                  "instructions": "string or null"
                }
              ]
            }

            ==== RULES ====
            - Do **not** infer or fabricate any unstated details.  
            - Use the tools for all code lookups; if still no match, `"code": null`.  
            - If ambiguous, explain in `"notes"` or `"instructions"`.
            - Return ONLY the raw JSON object, with no markdown formatting, code blocks, or explanatory text.

            ==== EXAMPLE ====
            **Input:**  
            "Assessment: Mild asthma exacerbation. Plan: Start albuterol inhaler PRN
            Initiate atorvastatin 20 mg PO daily qHS; discussed risks/benefits with pt

            Prescription Note:
            Atorvastatin 20mg tab Disp: #90 (ninety) tabs Sig: 1 tablet PO daily at bedtime Refills: 3.
            Omeprazole 20mg tab Disp: #90 (ninety) tabs Sig: 1 tablet PO daily at bedtime Refills: 3."

            **Output:**  
            {
              "patient": { "name": null, "id": null, "age": null, "gender": null, "dob": null, "additional_info": {} },
              "conditions": [
                { "text": "Mild asthma exacerbation", "code": "J45.901", "notes": "" }
              ],
              "medications": [
                {
                  "text": "albuterol inhaler PRN",
                  "code": "197361",
                  "dosage": null,
                  "route": "inhalation",
                  "frequency": "PRN",
                  "instructions": "Start"
                },
                {
                  "text": "atorvastatin 20mg po daily qHS",
                  "code": "597966",
                  "dosage": "20 mg",
                  "route": "PO",
                  "frequency": "qHS",
                  "instructions": "continue"
                },
                {
                  "text": "omeprazole 20mg po daily qHS",
                  "code": "617314",
                  "dosage": "20 mg",
                  "route": "PO",
                  "frequency": "daily",
              ]
            }
            """
        ).strip()

        # Create function tools that bind to this instance
        lookup_icd10_tool = function_tool(self._lookup_icd10)
        lookup_rxnorm_tool = function_tool(self._lookup_rxnorm)

        return Agent(
            name="Clinical Note Analyzer",
            instructions=system_prompt,
            tools=[lookup_icd10_tool, lookup_rxnorm_tool],
            model=self.model,
        )

    async def process_clinical_note(self, note_text: str) -> ClinicalNoteResponse:
        """Process a clinical note and extract structured information."""
        if not note_text:
            logger.warning("Empty note text provided")
            return ClinicalNoteResponse(
                patient=Patient(),
                conditions=[],
                medications=[],
                error="Empty note text provided",
            )

        try:
            # Create a new agent for each request
            logger.info("Creating new agent instance")
            agent = self._create_agent()

            # Run the agent with the note text
            logger.info("Running agent with note text")
            result = await Runner.run(
                starting_agent=agent,
                input=note_text,
            )

            # Get the output from the result
            if not hasattr(result, "final_output"):
                logger.error(
                    f"RunResult missing 'final_output' attribute. Available attributes: {dir(result)}"
                )
                raise ValueError("No final_output in agent response")

            if not result.final_output:
                logger.error("Empty final_output in agent response")
                raise ValueError("Empty final_output in agent response")

            logger.info("Successfully retrieved final_output from agent response")

            # Parse the response
            logger.info("Parsing JSON response")
            response_data = json.loads(result.final_output)

            # Create the response object
            logger.info("Creating ClinicalNoteResponse object")
            return ClinicalNoteResponse(
                patient=Patient(**response_data["patient"]),
                conditions=[Condition(**c) for c in response_data["conditions"]],
                medications=[Medication(**m) for m in response_data["medications"]],
            )

        except Exception as e:
            logger.error(f"Error processing clinical note: {str(e)}")
            return ClinicalNoteResponse(
                patient=Patient(),
                conditions=[],
                medications=[],
                error=str(e),
            )
