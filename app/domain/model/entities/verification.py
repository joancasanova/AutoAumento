# domain/model/entities/verification.py

from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class VerificationMode(Enum):
    """
    Defines how verification results are interpreted:
     - ELIMINATORY: If a method fails, the entire verification fails (discarded).
     - CUMULATIVE: Each successful method contributes to a success count toward final status.
    """
    ELIMINATORY = "eliminatory"
    CUMULATIVE = "cumulative"

@dataclass(frozen=True)
class VerificationThresholds:
    """
    Holds boundary values for a certain metric (e.g. success rate),
    optionally holding a target value that might be used by the verification logic.
    """
    lower_bound: float
    upper_bound: float
    target_value: Optional[float] = None

    def is_within_bounds(self, value: float) -> bool:
        """Check if 'value' is within the lower and upper bound range."""
        return self.lower_bound <= value <= self.upper_bound

@dataclass
class VerificationMethod:
    """
    Represents a single verification method or test that can be applied.
    For instance, it might define:
     - The system prompt, user prompt, valid responses, etc.
     - The number of sequences to generate from an LLM and the required_matches threshold.
     - The mode: ELIMINATORY or CUMULATIVE.
    """
    mode: VerificationMode
    name: str
    system_prompt: str
    user_prompt: str
    num_sequences: int
    valid_responses: List[str]
    required_matches: int
    max_tokens: int = 100
    temperature: float = 1.0

@dataclass(frozen=True)
class VerificationResult:
    """
    Describes the outcome of a single verification method:
     - Whether the method passed or failed.
     - An optional score, for instance ratio of positive responses.
     - Additional details, if needed.
    """
    method: VerificationMethod
    passed: bool
    score: Optional[float] = None
    details: Optional[Dict[str, any]] = None
    timestamp: datetime = datetime.now()

@dataclass
class VerificationSummary:
    """
    Contains the results of running all verification methods plus a final status.
    The final status can be 'confirmed', 'review', or 'discarded'.
    """
    results: List[VerificationResult]
    final_status: str
    reference_data: Optional[Dict[str, str]] = None
    
    @property
    def passed_methods(self) -> List[str]:
        """Returns the names of the methods that passed."""
        return [result.method.name for result in self.results if result.passed]
    
    @property
    def failed_methods(self) -> List[str]:
        """Returns the names of the methods that failed."""
        return [result.method.name for result in self.results if not result.passed]
    
    @property
    def success_rate(self) -> float:
        """Calculates the fraction of passed methods to total methods."""
        if not self.results:
            return 0.0
        return len(self.passed_methods) / len(self.results)

    @property
    def scores(self) -> List[Optional[float]]:
        """
        Collects the 'score' field from each verification result 
        and returns them as a list (useful for diagnostics).
        """
        return [result.score for result in self.results]

@dataclass
class VerifyRequest:
    """
    Describes what needs to be verified:
     - A list of VerificationMethods.
     - Thresholds for 'confirmed' or 'review'.
    """
    methods: List[VerificationMethod]
    required_for_confirmed: int
    required_for_review: int

@dataclass
class VerifyResponse:
    """
    Represents the final verification output, including:
     - VerificationSummary (with final_status).
     - Execution time and success rate stats.
    """
    verification_summary: VerificationSummary
    execution_time: float
    success_rate: float

@dataclass(frozen=True)
class VerificationStatus:
    """
    Helper dataclass to identify final statuses like 'confirmed', 'discarded', 'review'.
    """
    id: str
    status: str

    @classmethod
    def confirmed(cls):
       return cls(id="CONFIRMED", status="confirmed")
    
    @classmethod
    def discarded(cls):
       return cls(id="DISCARDED", status="discarded")

    @classmethod
    def review(cls):
       return cls(id="REVIEW", status="review")
    
    @classmethod
    def from_string(cls, status: str) -> Optional['VerificationStatus']:
        """
        Instantiates a VerificationStatus from a string identifier (if valid).
        """
        status = status.lower()
        if status == 'confirmed':
            return cls.confirmed()
        elif status == 'discarded':
             return cls.discarded()
        elif status == 'review':
            return cls.review()
        return None
        
    def is_final(self) -> bool:
        """
        Checks if the current status is 'confirmed' or 'discarded' (non-review).
        """
        return self in [self.confirmed(), self.discarded()]

    def requires_review(self) -> bool:
        """
        Checks if the current status is 'review'.
        """
        return self == self.review()
