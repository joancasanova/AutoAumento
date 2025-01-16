# domain/model/entities/generation.py

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

@dataclass(frozen=True)
class GenerationMetadata:
    """
    Stores metadata about the generation, such as:
     - Model name used.
     - Tokens used in the generation.
     - Time taken to generate the text.
     - Timestamp when the generation happened.
    """
    model_name: str
    system_prompt: str
    user_prompt: str
    temperature: float
    tokens_used: int
    generation_time: float
    timestamp: datetime = datetime.now()

@dataclass
class GeneratedResult:
    """
    Represents a single generated text sequence along with associated metadata.
    Optionally, it can store reference data that was substituted into the prompt.
    """
    content: str
    metadata: GenerationMetadata
    reference_data: Optional[Dict[str, str]] = None
    
    def to_dict(self):
        return {
            "content": self.content,
            "metadata": {
                "model_name": self.metadata.model_name,
                "system_prompt": self.metadata.system_prompt,
                "user_prompt": self.metadata.user_prompt,
                "temperature": self.metadata.user_prompt,
                "tokens_used": self.metadata.tokens_used,
                "generation_time": self.metadata.generation_time,
                "timestamp": self.metadata.timestamp.isoformat()  # Convert datetime to string
            },
            "reference_data": self.reference_data
        }
    
    def contains_reference(self, text: str) -> bool:
        """
        Checks if the given 'text' (case-insensitive) is present in the generated content.
        """
        return text.lower() in self.content.lower()
    
    def word_count(self) -> int:
        """
        Returns the word count of the generated content by splitting on whitespace.
        """
        return len(self.content.split())

@dataclass
class GenerateTextRequest:
    """
    Input data required to generate text:
     - system_prompt: The system-level instructions or context for the model.
     - user_prompt: The user's question or input prompt.
     - num_sequences: How many different responses should be generated.
     - max_tokens: Max tokens in the output.
     - temperature: Sampling temperature to control creativity.
    """
    system_prompt: str
    user_prompt: str
    num_sequences: int = 1
    max_tokens: int = 100
    temperature: float = 1.0

@dataclass
class GenerateTextResponse:
    """
    Output data returned from a text generation request:
     - generated_texts: A list of GeneratedResult items.
     - total_tokens: The sum of tokens used across all generated sequences.
     - generation_time: The total time taken to generate the text(s).
     - model_name: Name of the model used (from the first sequence, if available).
    """
    generated_texts: List[GeneratedResult]
    total_tokens: int
    generation_time: float
    model_name: str

    def to_dict(self):
        return {
            "generated_texts": [result.to_dict() for result in self.generated_texts],
            "total_tokens": self.total_tokens,
            "generation_time": self.generation_time,
            "model_name": self.model_name
        }