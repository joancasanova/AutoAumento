# application/use_cases/generate_text_use_case.py

import logging
from datetime import datetime
from domain.model.entities.generation import GenerateTextRequest, GenerateTextResponse
from domain.services.generate_service import GenerateService

logger = logging.getLogger(__name__)

class GenerateTextUseCase:
    """
    Orchestrates text generation using Large Language Models (LLMs).
    
    Handles full generation workflow including:
    - Input validation and sanitization
    - Prompt preparation and placeholder substitution
    - LLM execution through GenerateService
    - Performance metrics collection (tokens, timing)
    - Error handling and logging
    
    Attributes:
        generate_service: Service handling actual LLM interactions
    """

    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        Initializes text generation components with specified model.
        
        Args:
            model_name: Identifier for pretrained LLM. Defaults to Qwen2.5-1.5B.
                        Format should match HuggingFace model hub conventions.
        """
        # Dependency injection of generation service
        self.generate_service = GenerateService(model_name)

    def execute(self, request: GenerateTextRequest) -> GenerateTextResponse:
        """
        Executes end-to-end text generation process.
        
        Process Flow:
        1. Validate input prompts
        2. Execute LLM generation through service
        3. Calculate performance metrics
        4. Package results with metadata
        
        Args:
            request: Contains generation parameters including:
                    - System prompt (instructions/context)
                    - User prompt (direct query/input)
                    - Generation parameters (temperature, max_tokens, etc.)
        
        Returns:
            GenerateTextResponse: Contains generated texts and execution metadata
            
        Raises:
            ValueError: For invalid input prompts
            Exception: Propagates any errors from generation process
        """
        logger.info("Executing GenerateTextUseCase")
        self._validate_request(request)  # Primary input validation
        
        start_time = datetime.now()  # Precision timing started
        
        try:
            logger.debug("Extracting core prompts from request")
            # Direct prompt references for clarity
            system_prompt = request.system_prompt
            user_prompt = request.user_prompt

            # Core LLM execution block
            logger.debug("Initiating LLM generation process")
            generated_results = self.generate_service.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                num_sequences=request.num_sequences,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # Aggregate token usage across all generated sequences
            total_tokens = sum(result.metadata.tokens_used for result in generated_results)
            
            # Calculate precise generation duration
            generation_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Generated {len(generated_results)} sequence(s) in {generation_time:.4f}s with {total_tokens} tokens total.")
            
            return GenerateTextResponse(
                generated_texts=generated_results,
                total_tokens=total_tokens,
                generation_time=generation_time,
                # Safely handle empty results case
                model_name=generated_results[0].metadata.model_name if generated_results else "unknown"
            )
            
        except Exception as e:
            logger.exception("Critical error during text generation pipeline")
            # Preserve stack trace while propagating error
            raise e

    def _validate_request(self, request: GenerateTextRequest) -> None:
        """
        Ensures input prompts meet minimum requirements.
        
        Validation Rules:
        - System prompt must contain non-whitespace characters
        - User prompt must contain non-whitespace characters
        
        Args:
            request: Generation request to validate
            
        Raises:
            ValueError: For any validation failure with descriptive message
        """
        # System prompt validation
        if not request.system_prompt.strip():
            logger.error("Empty system prompt detected")
            raise ValueError("System prompt cannot be empty or whitespace.")
        
        # User prompt validation
        if not request.user_prompt.strip():
            logger.error("Empty user prompt detected")
            raise ValueError("User prompt cannot be empty or whitespace.")