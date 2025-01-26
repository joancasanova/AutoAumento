# domain/services/generate_service.py

import logging
import re
from typing import List
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datetime import datetime
from domain.model.entities.generation import GeneratedResult, GenerationMetadata

logger = logging.getLogger(__name__)

class GenerateService:
    """
    Text generation service using Hugging Face Transformers models.
    
    Handles:
    - Model and tokenizer initialization
    - Prompt formatting for different model types
    - Text generation with configurable parameters
    - Response post-processing and cleanup
    - Metadata collection and tracking

    Supports both base models and instruction-tuned models.
    """

    def __init__(self, model_name):
        """
        Initialize text generation service.

        Args:
            model_name: Hugging Face model identifier or local path

        Raises:
            Exception: If model loading fails
        """
        logger.info(f"Initializing generator with model '{model_name}'.")
        self.model_name = model_name
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.instruct_mode = "instruct" in model_name.lower()  # Detect instruction-tuned models

        try:
            # Initialize tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            self.model.to(self.device)  # Move model to appropriate device
            logger.info(f"Successfully loaded model on {self.device.upper()}")
        except Exception as e:
            logger.exception("Model loading failed")
            raise RuntimeError(f"Could not load model {model_name}") from e

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        num_sequences: int = 1,
        max_tokens: int = 100,
        temperature: float = 1.0
    ) -> List[GeneratedResult]:
        """
        Generate text sequences from prompts.

        Args:
            system_prompt: Context/instructions for the model
            user_prompt: Specific input/question to generate response for
            num_sequences: Number of variations to generate (default: 1)
            max_tokens: Maximum length of generated text (default: 100)
            temperature: Sampling randomness (0.0=deterministic, 1.0=default)

        Returns:
            List[GeneratedResult]: Generated text sequences with metadata

        Raises:
            Exception: If generation fails
        """
        logger.debug(f"Generating with system prompt: {system_prompt[:50]}...")
        start_time = datetime.now()
        
        try:
            # Format prompt based on model type
            if self.instruct_mode:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                prompt = f"{system_prompt}\n{user_prompt}"

            # Tokenize and generate
            inputs = self.tokenizer([prompt], return_tensors="pt").to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                num_return_sequences=num_sequences,
                do_sample=True,
                temperature=temperature,
                pad_token_id=self.tokenizer.eos_token_id
            )

            # Process outputs
            decoded_outputs = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
            return self._create_results(decoded_outputs, prompt, system_prompt, user_prompt, temperature, start_time)

        except Exception as e:
            logger.exception("Generation failed")
            raise

    def get_token_count(self, text: str) -> int:
        """
        Calculate token count for a given text string.

        Args:
            text: Input text to analyze

        Returns:
            int: Number of tokens in the text

        Raises:
            Exception: If tokenization fails
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.exception("Token counting error")
            raise

    def _create_results(self, outputs: List[str], prompt: str, system_prompt: str,
                       user_prompt: str, temperature: float, start_time: datetime) -> List[GeneratedResult]:
        """Package raw outputs into GeneratedResult objects with metadata."""
        results = []
        for output in outputs:
            content = self._process_output(output, prompt)
            metadata = GenerationMetadata(
                model_name=self.model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                tokens_used=len(self.tokenizer.encode(content)),
                generation_time=(datetime.now() - start_time).total_seconds()
            )
            results.append(GeneratedResult(content=content.strip(), metadata=metadata))
        logger.debug(f"Generated {len(results)} sequences")
        return results

    def _extract_assistant_response(self, text: str) -> str:
        """
        Extract assistant's response from instruction-formatted text.
        
        Uses pattern matching to find content after 'assistant' marker.
        """
        match = re.search(r"assistant\n(.*)", text, re.DOTALL)
        return match.group(1).strip() if match else text.strip()

    def _trim_response(self, prompt: str, output: str) -> str:
        """
        Remove prompt text from generated output.
        
        Handles cases where model doesn't exactly reproduce prompt.
        """
        return output[len(prompt):].strip() if output.startswith(prompt) else output.strip()

    def _process_output(self, output: str, prompt: str) -> str:
        """Select appropriate processing method based on model type."""
        return self._extract_assistant_response(output) if self.instruct_mode else self._trim_response(prompt, output)