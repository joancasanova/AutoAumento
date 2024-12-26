# app/domain/model/entities/pipeline.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from app.domain.model.entities.generation import GenerateTextRequest
from app.domain.model.entities.parsing import ParseRequest
from app.domain.model.entities.verification import VerifyRequest

@dataclass
class PipelineStep:
    """
    Define un solo paso en el pipeline.
    - name: Nombre único del paso.
    - type: Tipo de paso ('generate', 'parse', 'verify').
    """
    name: str
    type: str

@dataclass
class PipelineRequest:
    """
    Describe el pipeline completo a ejecutar.
    - steps: Lista de PipelineStep indicando el orden y el tipo de cada paso.
    - parameters: Diccionario que mapea nombres de pasos a sus respectivas dataclasses de request.
    - global_reference_data: Diccionario opcional con datos globales para placeholders.
    """
    steps: List[PipelineStep]
    parameters: Dict[str, Union[GenerateTextRequest, ParseRequest, VerifyRequest]]
    global_reference_data: Optional[Dict[str, Any]] = None

@dataclass
class PipelineResponse:
    """
    Respuesta final del pipeline, con los resultados agregados de todos los pasos.
    - step_results: Lista de diccionarios, donde cada diccionario contiene la información y
                    resultados de un paso del pipeline.
    """
    step_results: List[Dict[str, Any]]