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
    Concrete implementation of GenerateService using Hugging Face Transformers library.
    This class is intended for an instruct-style model, potentially Chat-like.
    """

    def __init__(self, model_name):
        """
        Initialize the model, tokenizer, and other relevant settings.
        By default, it attempts to use GPU if available.
        """
        logger.info(f"Initializing InstructModel with model name '{model_name}'.")
        self.model_name = model_name
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.instruct_mode = "instruct" in model_name.lower()
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)
            self.model.to(self.device)
            logger.info(f"Model '{model_name}' loaded successfully on device '{self.device}'.")
        except Exception as e:
            logger.exception(f"Failed to load model '{model_name}'.")
            raise e

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        num_sequences: int = 1,
        max_tokens: int = 100,
        temperature: float = 1.0
    ) -> List[GeneratedResult]:
        """
        Generate one or more sequences of text from the model:
         1) Construct the prompt (depending on instruct mode).
         2) Tokenize the prompt.
         3) Call the model.generate() function.
         4) Decode and trim the model outputs.
         5) Build a list of GeneratedResult objects with metadata for each sequence.
        """
        logger.debug(f"generate() called with system_prompt='{system_prompt[:50]}...', user_prompt='{user_prompt[:50]}...'.")
        start_time = datetime.now()
        
        try:
            # If in instruct mode, format messages accordingly
            if self.instruct_mode:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                # apply_chat_template is hypothetical
                prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                prompt = f"{system_prompt}\n{user_prompt}"

            inputs = self.tokenizer([prompt], return_tensors="pt").to(self.device)
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                num_return_sequences=num_sequences,
                do_sample=True,
                temperature=temperature,
                pad_token_id=self.tokenizer.eos_token_id
            )

            decoded_outputs = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

            results = []
            for output in decoded_outputs:
                if self.instruct_mode:
                    content = self._extract_assistant_response(output)
                else:
                    content = self._trim_response(prompt, output)

                metadata = GenerationMetadata(
                    model_name=self.model_name,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    tokens_used=len(self.tokenizer.encode(content)),
                    generation_time=(datetime.now() - start_time).total_seconds()
                )

                results.append(GeneratedResult(content=content.strip(), metadata=metadata))

            logger.debug(f"Generated {len(results)} sequences with model '{self.model_name}'.")
            return results

        except Exception as e:
            logger.exception("Error during model generation.")
            raise e

    def get_token_count(self, text: str) -> int:
        """
        Helper method to compute the number of tokens in a given text string.
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.exception("Error counting tokens.")
            raise e

    def _extract_assistant_response(self, text: str) -> str:
        """
        Extracts the 'assistant' role answer from instruct-style output.
        """
        match = re.search(r"assistant\n(.*)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
    
    def _trim_response(self, prompt, output):
        """
        Removes the prompt text from the full output to isolate only the newly generated part.
        """
        if output.startswith(prompt):
            return output[len(prompt):].strip()
        else:
            return output
