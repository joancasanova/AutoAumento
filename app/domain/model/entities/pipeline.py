# app/domain/model/entities/pipeline.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from domain.model.entities.generation import GenerateTextRequest
from domain.model.entities.parsing import ParseRequest
from domain.model.entities.verification import VerifyRequest

@dataclass
class PipelineStep:
    """
    Represents a single step in the processing pipeline.

    Attributes:
        type: The type of processing step. Valid values:
              - 'generate': Text generation step
              - 'parse': Text parsing step
              - 'verify': Result verification step
        parameters: Configuration specific to the step type. Must match:
                   - GenerateTextRequest for 'generate' steps
                   - ParseRequest for 'parse' steps
                   - VerifyRequest for 'verify' steps
        uses_reference: Flag indicating if this step uses reference data 
                       from previous steps
        reference_step_numbers: List of step indices (0-based) providing 
                               reference data. Ordered by priority.
    """
    type: str
    parameters: Union[GenerateTextRequest, ParseRequest, VerifyRequest]
    uses_reference: bool = False
    reference_step_numbers: Optional[List[int]] = None

@dataclass
class PipelineRequest:
    """
    Complete configuration for executing a processing pipeline.

    Attributes:
        steps: Ordered list of PipelineStep objects defining the 
              processing workflow
        global_references: Optional shared reference data available 
                          to all steps through {placeholder} syntax
    """
    steps: List[PipelineStep]
    global_references: Optional[Dict[str, str]] = None

@dataclass
class PipelineResponse:
    """
    Aggregated results from executing a processing pipeline.

    Attributes:
        step_results: List of dictionaries containing raw outputs 
                     from each step, preserving execution order
        verification_references: Categorized references from 
                                verification steps with keys:
                                - 'confirmed': Verified valid results
                                - 'to_verify': Results needing manual review
    """
    step_results: List[Dict[str, Any]]    
    verification_references: Dict[str, List]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the pipeline response to a dictionary format.
        
        Returns:
            Dictionary with keys:
            - step_results: Serialized step outputs
            - verification_references: Direct reference to verification categories
        """
        return {
            "step_results": self.step_results,
            "verification_references": self.verification_references
        }