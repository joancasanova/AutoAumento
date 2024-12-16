# application/use_cases/generation/generate_text_use_case.py

import logging
from datetime import datetime
from domain.model.entities.generation import GenerateTextRequest, GenerateTextResponse
from domain.services.placeholder_service import PlaceholderService
from domain.ports.llm_port import LLMPort

logger = logging.getLogger(__name__)

class GenerateTextUseCase:
    """
    Use case responsible for generating text using an LLM (Language Model).
    It handles placeholder replacement, timing, token counting, and error management.
    """

    def __init__(self, llm: LLMPort):
        """
        Initializes the use case with a specific LLM port (interface).
        Also instantiates a placeholder service to handle placeholders
        in system prompts and user prompts.
        """
        self.llm = llm
        self.placeholder_service = PlaceholderService()

    def execute(self, request: GenerateTextRequest) -> GenerateTextResponse:
        """
        Executes the text generation flow:
         1) Validate request inputs (prompt strings).
         2) Manage placeholders if reference data is provided.
         3) Call the underlying LLM to generate multiple sequences.
         4) Measure generation time and compute total tokens used.
         5) Return a response object with the generated results.
        """
        logger.info("Executing GenerateTextUseCase")
        self._validate_request(request)
        
        start_time = datetime.now()
        
        try:
            logger.debug("Extracting prompts and reference data for placeholders")
            system_prompt = request.system_prompt
            user_prompt = request.user_prompt
            
            # If reference data is provided, extract placeholders and replace them
            if request.reference_data:
                all_placeholders = (
                    self.placeholder_service.extract_placeholders(system_prompt) |
                    self.placeholder_service.extract_placeholders(user_prompt)
                )
                
                if all_placeholders:
                    logger.debug("Found placeholders, performing substitution.")
                    system_prompt = self.placeholder_service.validate_and_replace_placeholders(
                        system_prompt, 
                        request.reference_data
                    )
                    user_prompt = self.placeholder_service.validate_and_replace_placeholders(
                        user_prompt, 
                        request.reference_data
                    )

            # Generate text using the LLM
            logger.debug("Invoking LLMPort.generate() method")
            generated_results = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                num_sequences=request.num_sequences,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            total_tokens = sum(result.metadata.tokens_used for result in generated_results)
            generation_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Generated {len(generated_results)} sequence(s) in {generation_time:.4f}s with {total_tokens} tokens total.")
            return GenerateTextResponse(
                generated_texts=generated_results,
                total_tokens=total_tokens,
                generation_time=generation_time,
                model_name=generated_results[0].metadata.model_name if generated_results else "unknown"
            )
            
        except Exception as e:
            logger.exception("Error during text generation.")
            raise e

    def _validate_request(self, request: GenerateTextRequest) -> None:
        """
        Basic input validation: system_prompt and user_prompt must not be empty.
        Raises an exception if either prompt is blank.
        """
        if not request.system_prompt.strip():
            logger.error("System prompt cannot be empty or whitespace.")
            raise ValueError("System prompt cannot be empty or whitespace.")
        if not request.user_prompt.strip():
            logger.error("User prompt cannot be empty or whitespace.")
            raise ValueError("User prompt cannot be empty or whitespace.")
