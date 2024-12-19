# app/domain/model/entities/pipeline.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PipelineStep:
    """
    Defines a single pipeline step configuration:
    - step_type: 'generate', 'parse', or 'verify'
    - params: Dictionary containing any parameters needed for the step
    """
    step_type: str
    params: Dict[str, Any]


@dataclass
class PipelineRequest:
    """
    Describes the entire pipeline to be executed:
    - steps: A list of PipelineStep objects indicating the pipeline order and parameters
    - global_reference_data: Optional dictionary with placeholders or global data
    """
    steps: List[PipelineStep]
    global_reference_data: Optional[Dict[str, Any]] = None


@dataclass
class PipelineStepResult:
    """
    Holds the result of a single pipeline step execution:
    - step_type: Which step was executed ('generate', 'parse', 'verify', etc.)
    - input_data: The input fed into this step
    - output_data: The output returned by this step
    """
    step_type: str
    input_data: Any
    output_data: Any


@dataclass
class PipelineResponse:
    """
    Final pipeline response, containing the aggregated results of all steps:
    - step_results: A list of PipelineStepResult for each step executed in the pipeline
    """
    step_results: List[PipelineStepResult]
