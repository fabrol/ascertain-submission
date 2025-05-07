import aiohttp
from typing import Optional, Dict, List, Tuple, Any
import logging
from pydantic import BaseModel
from src.config import settings
from src.services.llm_service import LLMService
from src.services.example_store import ExampleStore, CodeExample
from textwrap import dedent
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MedicalCodeResult(BaseModel):
    """Result from a medical code lookup."""

    code: Optional[str]
    description: Optional[str]
    confidence: Optional[float] = None
    additional_info: Dict = {}


class MedicalCodeService:
    """
    Service for looking up medical codes (ICD-10 and RxNorm) using OpenAI's API.
    """

    # RxNav API base URL
    RXNAV_API_BASE = "https://rxnav.nlm.nih.gov/REST"

    # ICD-10 API - using the UMLS API for ICD-10 lookups
    ICD10_API_BASE = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"

    # Model to use for medical code lookups
    MEDICAL_CODE_MODEL = "gpt-4o-mini"  # Model optimized for medical code lookups

    def __init__(
        self, db: Optional[Session] = None, llm_service: Optional[LLMService] = None
    ):
        """
        Initialize the medical code service.

        Args:
            db: Optional SQLAlchemy database session for caching
            llm_service: Optional LLM service instance to use
        """
        if not settings.is_openai_configured():
            raise ValueError(
                "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            )

        self.db = db
        self.model = "gpt-4o-mini"  # Using a capable model for code lookups
        self.llm_service = llm_service or LLMService(db=db)
        self.example_store = ExampleStore(db=db, llm_service=self.llm_service)

    async def _extract_drug_name(self, free_text: str) -> Optional[str]:
        """Extract drug name and relevant details from free text using LLM."""
        try:
            logger.info(f"Extracting drug name from text: {free_text}")
            system_prompt = (
                "Extract the drug name and relevant medication details from text to set it up for RxNorm lookup.\n"
                "Preserve important medication information like dosage (e.g., 20mg), form (e.g., tablet -> tab, syrup), and strength.\n"
                "Remove only extraneous information like frequency, patient instructions, or non-medication related text.\n\n"
                "Examples:\n"
                '"Patient was prescribed Atorvastatin 20mg tablet" -> "atorvastatin 20mg tab"\n'
                '"Taking metformin 500mg twice daily" -> "metformin 500mg"\n'
                '"Give amoxicillin 250mg/5ml syrup" -> "amoxicillin 250mg/5ml syrup"\n'
                '"Prescribed lisinopril 10 mg tablet" -> "lisinopril 10mg tablet"\n\n'
                "Return the cleaned medication text in lowercase, preserving important medication details."
            )

            result = await self.llm_service.process_prompt(
                system_prompt=system_prompt,
                user_prompt=f"Extract the medication details from: {free_text}",
                model=self.MEDICAL_CODE_MODEL,
                temperature=0.1,
            )

            if result.error:
                logger.error(f"Error extracting drug name: {result.error}")
                return None

            extracted_text = result.content.strip().lower()
            logger.info(f"Extracted drug text: {extracted_text}")
            return extracted_text
        except Exception as e:
            logger.error(f"Error extracting drug name: {str(e)}")
            return None

    async def lookup_rxnorm(self, free_text: str) -> Optional[MedicalCodeResult]:
        """Look up RxNorm code from free text.

        Flow:
        1. Extract drug name and details from free text using LLM
        2. Find RxNorm code using approximateTerm with Active concepts
        3. Return the code and description if found
        """
        try:
            # Extract drug name from free text
            drug_text = await self._extract_drug_name(free_text)
            if not drug_text:
                logger.warning("Could not extract drug information from text")
                return MedicalCodeResult(
                    code=None,
                    description=None,
                    confidence=None,
                    additional_info={"error": "Could not extract drug information from text"}
                )

            # Get similar examples to enhance the lookup
            similar_examples = await self.example_store.get_similar_examples(
                drug_text, example_type="medication", top_k=3
            )
            
            # If we have a high-confidence exact match in examples, use it directly
            for example in similar_examples:
                if example.text.lower() == drug_text.lower() and example.confidence > 0.9:
                    logger.info(f"Found exact match in examples: {example.code} - {example.description}")
                    return MedicalCodeResult(
                        code=example.code,
                        description=example.description,
                        confidence=example.confidence,
                        additional_info={"source": "example_store", "original_query": free_text}
                    )

            # Step 2: Find RxNorm code using API
            async with aiohttp.ClientSession() as session:
                result = await self._try_approximate_match(session, drug_text)
                
                # If we got a result with high confidence, return it
                if result and result.confidence and result.confidence > 0.8:
                    # Store this as a new example for future use
                    await self.example_store.add_example(
                        CodeExample(
                            text=drug_text,
                            code=result.code,
                            description=result.description,
                            type="medication",
                            source="rxnav_api",
                            confidence=result.confidence
                        )
                    )
                    return result
                
                # If we have similar examples but no high-confidence match, use LLM to decide
                if not result:
                    logger.debug(f"No direct match found for {drug_text}, trying enhanced lookup")
                    result = await self._enhanced_code_lookup(
                        drug_text, 
                        None,  # api_result
                        similar_examples,
                        "medication"  # code_type
                    )
                    
                # If still no match, return None
                if not result:
                    return None
                    
                return result

        except Exception as e:
            logger.error(f"Error looking up RxNorm code for {free_text}: {str(e)}")
            return None

    async def _try_approximate_match(
        self, session: aiohttp.ClientSession, drug_text: str
    ) -> Optional[MedicalCodeResult]:
        """Try to find an RxNorm match using approximateTerm with Active concepts.

        Args:
            session: The aiohttp session to use for API calls
            drug_text: The drug text to search for

        Returns:
            MedicalCodeResult with the best match, or None if no match found
        """
        try:
            # Get similar examples to enhance the lookup
            similar_examples = await self.example_store.get_similar_examples(
                drug_text, example_type="medication", top_k=3
            )
            
            logger.debug(f"Attempting approximate match for: {drug_text}")
            async with session.get(
                f"{self.RXNAV_API_BASE}/approximateTerm.json",  # Use JSON format
                params={
                    "term": drug_text,
                    "maxEntries": 5,
                    "option": 1,  # Find atoms in Active concepts
                },
            ) as response:
                if response.status != 200:
                    logger.debug(
                        f"Approximate match API returned status: {response.status}"
                    )
                    return None

                data = await response.json()
                logger.debug(f"Received JSON response: {data}")

                if not data or "approximateGroup" not in data:
                    logger.debug("No approximate matches found in response")
                    return None

                candidates = []
                # Process candidates from the JSON response
                for candidate in data["approximateGroup"].get("candidate", []):
                    # Skip candidates without required fields
                    if not all(
                        key in candidate for key in ["rxcui", "name", "score", "rank"]
                    ):
                        logger.debug(f"Skipping invalid candidate: {candidate}")
                        continue

                    # Skip candidates without text content
                    if not all(candidate[key] for key in ["rxcui", "name"]):
                        logger.debug(f"Skipping empty candidate: {candidate}")
                        continue

                    # Skip if we already have this rxcui
                    if any(c["rxcui"] == candidate["rxcui"] for c in candidates):
                        logger.debug(f"Skipping duplicate rxcui: {candidate['rxcui']}")
                        continue

                    try:
                        score_value = float(candidate["score"])
                        rank_value = int(candidate["rank"])
                        candidates.append(
                            {
                                "rxcui": candidate["rxcui"],
                                "name": candidate["name"],
                                "score": score_value,
                                "rank": rank_value,
                                "source": candidate.get("source", "UNKNOWN"),
                            }
                        )
                        logger.debug(
                            f"Added candidate: {candidate['name']} id: {candidate['rxcui']} (score: {score_value}, rank: {rank_value}, source: {candidate.get('source', 'UNKNOWN')})"
                        )
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Error processing candidate score/rank: {str(e)}")
                        continue

                if not candidates:
                    logger.debug("No valid candidates found after processing")
                    return None

                # Sort candidates by rank and score
                candidates.sort(key=lambda x: (x["rank"], -x["score"]))

                # Format candidates for LLM selection (1-based indexing for user-friendly display)
                candidates_text = "\n".join(
                    f"{i+1}. {c['name']} (Score: {c['score']:.2f}, Rank: {c['rank']}, Source: {c['source']})"
                    for i, c in enumerate(candidates)
                )
                logger.debug(
                    f"Presenting {len(candidates)} candidates to LLM:\n{candidates_text}"
                )

                # If we have similar examples, include them in the LLM prompt
                examples_text = ""
                if similar_examples:
                    formatted_examples = await self.example_store.format_examples_for_prompt(similar_examples)
                    examples_text = "Similar examples from our database:\n" + formatted_examples
                    logger.debug(f"Including {len(similar_examples)} similar examples in prompt")

                # Use LLM to select the best match
                system_prompt = (
                    "You are a medical coding expert. Given a drug name and a list of potential RxNorm matches, "
                    "select the most appropriate match. Consider both the drug name and the match score. "
                    f"{examples_text}\n\n"
                    "Return ONLY the number of the best match (1-5). If none seem appropriate, return 0."
                )

                result = await self.llm_service.process_prompt(
                    system_prompt=system_prompt,
                    user_prompt=(
                        f"Original drug query: {drug_text}\n\n"
                        "Potential matches:\n"
                        f"{candidates_text}\n\n"
                        "Select the most appropriate match (1-5) or 0 if none match:"
                    ),
                    model=self.MEDICAL_CODE_MODEL,
                    temperature=0.1,
                )

                if result.error:
                    logger.error(f"Error selecting RxNorm match: {result.error}")
                    return None

                # Convert 1-based LLM selection to 0-based array index
                selected_index = int(result.content.strip())
                logger.debug(f"LLM selected index: {selected_index}")

                # Validate selection (0 means no match, > len(candidates) is invalid)
                if selected_index == 0 or selected_index > len(candidates):
                    logger.debug("LLM rejected all matches or selected invalid index")
                    return None

                # Get the selected candidate (convert from 1-based to 0-based index)
                selected = candidates[selected_index - 1]
                logger.debug(
                    f"Selected candidate: {selected['name']} id: {selected['rxcui']} (score: {selected['score']}, rank: {selected['rank']}, source: {selected['source']})"
                )

                # Create the result
                result = MedicalCodeResult(
                    code=selected["rxcui"],
                    description=selected["name"].lower(),
                    confidence=selected["score"] / 100.0,
                    additional_info={
                        "rank": selected["rank"],
                        "source": selected["source"],
                    },
                )
                
                # If confidence is high, add to examples
                if result.confidence and result.confidence > 0.8:
                    await self.example_store.add_example(
                        CodeExample(
                            text=drug_text,
                            code=result.code,
                            description=result.description,
                            type="medication",
                            source="rxnav_api",
                            confidence=result.confidence
                        )
                    )
                    
                return result

        except Exception as e:
            logger.error(f"Unexpected error in approximate match: {str(e)}")
            return None

    async def lookup_icd10(self, condition_name: str) -> Optional[MedicalCodeResult]:
        """
        Look up ICD-10 code for a condition using the NLM Clinical Tables API and LLM for best match selection.

        Args:
            condition_name: Name of the condition to look up

        Returns:
            MedicalCodeResult object with ICD-10 code and description if found
        """
        try:
            # Get similar examples to enhance the lookup
            similar_examples = await self.example_store.get_similar_examples(
                condition_name, example_type="condition", top_k=3
            )
            
            # If we have a high-confidence exact match in examples, use it directly
            for example in similar_examples:
                if example.text.lower() == condition_name.lower() and example.confidence > 0.9:
                    logger.info(f"Found exact match in examples: {example.code} - {example.description}")
                    return MedicalCodeResult(
                        code=example.code,
                        description=example.description,
                        confidence=example.confidence,
                        additional_info={"source": "example_store", "original_query": condition_name}
                    )

            # Continue with API lookup
            async with aiohttp.ClientSession() as session:
                url = self.ICD10_API_BASE
                params = {
                    "terms": condition_name.lower(),  # Convert to lowercase for search
                    "df": "code,name",  # Return code and name
                    "cf": "true",  # Return confidence scores
                    "sf": "name",  # Search by name
                    "maxList": 5,  # Return top 5 matches for LLM to choose from
                }

                logger.debug(f"Making ICD-10 API request with params: {params}")

                async with session.get(url, params=params) as response:
                    if not response.ok:
                        error_text = await response.text()
                        logger.warning(
                            f"ICD-10 API error: {response.status} - {error_text}"
                        )
                        return None

                    data = await response.json()
                    logger.debug(f"ICD-10 API response: {data}")

                    if not data or len(data) < 4 or not data[3]:
                        logger.debug("No ICD-10 results found")
                        return None

                    # Extract results
                    # Format: [total_count, skip, data_format, [[code, name]]]
                    results = data[3]
                    if not results:
                        logger.debug("No ICD-10 results in response")
                        return MedicalCodeResult(code=None, description=None)

                    # If we have similar examples, include them in the LLM prompt
                    examples_text = ""
                    if similar_examples:
                        formatted_examples = await self.example_store.format_examples_for_prompt(similar_examples)
                        examples_text = "Similar examples from our database:\n" + formatted_examples

                    # Prepare results for LLM selection
                    results_text = "\n".join(
                        [
                            f"{i+1}. {result[1]} (Code: {result[0]})"
                            for i, result in enumerate(results)
                        ]
                    )

                    # Use LLM to select the best match
                    system_prompt = (
                        "You are a medical coding expert. Given a condition and a list of potential ICD-10 codes, "
                        "select the most appropriate match. Consider both the condition description and the ICD-10 code context. "
                        f"{examples_text}\n\n"
                        "Return ONLY the number of the best match (1-5). If none seem appropriate, return 0."
                    )

                    result = await self.llm_service.process_prompt(
                        system_prompt=system_prompt,
                        user_prompt=(
                            f"Original condition: {condition_name}\n\n"
                            "Potential matches:\n"
                            f"{results_text}\n\n"
                            "Select the most appropriate match (1-5) or 0 if none match:"
                        ),
                        model=self.MEDICAL_CODE_MODEL,
                        temperature=0.1,
                    )

                    if result.error:
                        logger.error(f"Error selecting ICD-10 match: {result.error}")
                        return None

                    selected_index = int(result.content.strip())

                    if selected_index == 0 or selected_index > len(results):
                        logger.debug("LLM rejected all matches")
                        return MedicalCodeResult(code=None, description=None)

                    # Get the selected result
                    result = results[selected_index - 1]
                    code = result[0]
                    name = result[1].lower()  # Convert to lowercase

                    # Calculate confidence (if available)
                    confidence = None
                    if len(data) > 4 and data[4]:
                        confidence = (
                            float(data[4][selected_index - 1]) / 100
                        )  # Normalize to 0-1
                        logger.debug(f"ICD-10 match confidence: {confidence}")

                    # Store this as a new example for future use if confidence is high
                    if confidence and confidence > 0.8:
                        await self.example_store.add_example(
                            CodeExample(
                                text=condition_name,
                                code=code,
                                description=name,
                                type="condition",
                                source="icd10_api",
                                confidence=confidence
                            )
                        )

                    logger.debug(f"Found ICD-10 code: {code} - {name}")
                    return MedicalCodeResult(
                        code=code,
                        description=name.lower(),
                        confidence=confidence,
                        additional_info={"original_query": condition_name},
                    )

        except Exception as e:
            logger.error(f"Error looking up ICD-10 code for {condition_name}: {str(e)}")
            return None
            
    async def _enhanced_code_lookup(
        self, 
        text: str, 
        api_result: Optional[MedicalCodeResult], 
        similar_examples: List[CodeExample],
        code_type: str
    ) -> Optional[MedicalCodeResult]:
        """
        Use LLM with similar examples to enhance code lookup results.
        
        Args:
            text: The original text to look up
            api_result: The result from the API lookup (may be None)
            similar_examples: Similar examples from the example store
            code_type: The type of code ("medication" or "condition")
            
        Returns:
            Enhanced MedicalCodeResult
        """
        try:
            # Format examples for the prompt
            formatted_examples = await self.example_store.format_examples_for_prompt(similar_examples)
            examples_text = formatted_examples
            
            # Format API result if available
            api_result_text = "No API result found."
            if api_result and api_result.code:
                api_result_text = f"API Result:\nCode: {api_result.code}\nDescription: {api_result.description}\nConfidence: {api_result.confidence or 'Unknown'}"
            
            # Create system prompt
            system_prompt = f"""
            You are a medical coding expert specializing in {code_type} codes.
            Based on similar examples and API results, determine the most appropriate code for the given text.
            
            Similar examples from our database:
            {examples_text}
            
            {api_result_text}
            
            Analyze the input text carefully and compare it to the examples.
            Return a JSON object with the following fields:
            - code: The most appropriate code
            - description: The description of the code
            - confidence: Your confidence in this match (0.0-1.0)
            - reasoning: Brief explanation of your decision
            """
            
            # Call LLM
            result = await self.llm_service.process_prompt(
                system_prompt=system_prompt,
                user_prompt=f"Find the most appropriate {code_type} code for: {text}",
                model=self.MEDICAL_CODE_MODEL,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            if result.error:
                logger.error(f"Error in enhanced code lookup: {result.error}")
                return api_result  # Fall back to API result
                
            # Parse the response
            import json
            response_data = json.loads(result.content)
            
            # Create result
            code = response_data.get("code")
            
            # If code is 'N/A' or empty, return None
            if not code or code == 'N/A':
                return None
                
            enhanced_result = MedicalCodeResult(
                code=code,
                description=response_data.get("description"),
                confidence=response_data.get("confidence"),
                additional_info={
                    "reasoning": response_data.get("reasoning"),
                    "original_query": text,
                    "source": "enhanced_llm"
                }
            )
            
            # If confidence is high, add to examples
            if enhanced_result.confidence and enhanced_result.confidence > 0.8:
                await self.example_store.add_example(
                    CodeExample(
                        text=text,
                        code=enhanced_result.code,
                        description=enhanced_result.description,
                        type=code_type,
                        source="enhanced_llm",
                        confidence=enhanced_result.confidence
                    )
                )
                
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in enhanced code lookup: {str(e)}")
            return api_result  # Fall back to API result
