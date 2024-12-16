# domain/ports/llm_port.py

from abc import ABC, abstractmethod
from typing import List
from domain.model.entities.generation import GeneratedResult

class LLMPort(ABC):
    """
    Abstract base class (interface) for any LLM (Language Model) integration.
    It enforces the implementation of a 'generate' method that returns
    a list of GeneratedResult objects.
    """
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        num_sequences: int = 1,
        max_tokens: int = 100,
        temperature: float = 1.0
    ) -> List[GeneratedResult]:
        """
        Generate text using the language model.
        
        Args:
            system_prompt: System-level instructions for the model.
            user_prompt: User input or question.
            num_sequences: Number of different sequences to generate.
            max_tokens: Maximum number of tokens to generate.
            temperature: Sampling temperature for the generation process.
            
        Returns:
            A list of GeneratedResult objects containing the generated text and metadata.
        """
        pass
