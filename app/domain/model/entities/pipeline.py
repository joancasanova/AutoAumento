# app/domain/model/entities/pipeline.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

from app.domain.model.entities.generation import GenerateTextRequest
from app.domain.model.entities.parsing import ParseRequest
from app.domain.model.entities.verification import VerifyRequest

@dataclass
class PipelineStep:
    """
    Define un solo paso en el pipeline.

    - name: Nombre único del paso.
    - type: Tipo de paso ('generate', 'parse', 'verify').
    - parameters: Parámetros específicos para el paso actual (especificados externamente).
    - uses_reference: Indica si este paso utiliza datos de referencia.
    - reference_step_names: Indica el orden de prioridad donde buscar los datos de referencia.
    - uses_verification: Indica si este paso se ejecuta dependiendo del resultado de una verificación.
    - verification_status: Indica el nombre de un paso de verificación previo y resultado deseado de esta ('confirmed', 'review', or 'discarded').
    """
    name: str
    type: str
    parameters: Union[GenerateTextRequest, ParseRequest, VerifyRequest]
    uses_reference: bool = False
    reference_step_names: Optional[List[str]] = None
    uses_verification: bool = False
    verification_step: Optional[Tuple[str, str]] = None

@dataclass
class PipelineRequest:
    """
    Describe el pipeline completo a ejecutar.

    - steps: Lista de PipelineStep indicando el orden y el tipo de cada paso.
    - global_reference_data: Diccionario opcional con datos globales para placeholders.
    """
    steps: List[PipelineStep]
    global_reference_data: Optional[Dict[str, Any]] = None

@dataclass
class PipelineResponse:
    """
    Respuesta final del pipeline, con los resultados agregados de todos los pasos.

    - step_results: Lista de diccionarios, donde cada diccionario contiene la información y
                    resultados de un paso del pipeline.
    """
    step_results: List[Dict[str, Any]]