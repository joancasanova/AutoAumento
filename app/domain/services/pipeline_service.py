# app/domain/services/pipeline_service.py

import logging
from typing import Any, Dict, List, Optional, Union
import json
import copy

from app.application.use_cases.generate_text_use_case import GenerateTextUseCase, GenerateTextRequest
from app.application.use_cases.parse_generated_output_use_case import ParseGeneratedOutputUseCase, ParseRequest
from app.application.use_cases.verify_use_case import VerifyUseCase, VerifyRequest
from app.domain.services.parse_service import ParseService
from app.domain.services.verifier_service import VerifierService
from app.infrastructure.external.llm.instruct_model import InstructModel

from app.domain.model.entities.generation import GeneratedResult
from app.domain.model.entities.parsing import ParseMode, ParseRule
from app.domain.model.entities.verification import (
    VerificationMethod,
    VerificationMode,
    VerifyResponse
)
from app.domain.model.entities.pipeline import PipelineStep

logger = logging.getLogger(__name__)

class PipelineService:
    """
    PipelineService maneja la ejecución secuencial de los pasos en un pipeline.
    Cada paso puede ser 'generate', 'parse', o 'verify', y toma la
    salida del paso previo como su entrada.

    Almacena los resultados intermedios de cada paso y permite exportarlos a JSON.
    """

    def __init__(self, llm: InstructModel):
        """
        Inicializa el PipelineService.

        Args:
            llm (InstructModel): Modelo LLM pre-instanciado para generación de texto.
        """
        self.llm = llm
        self.reference_data_store: Dict[str, Any] = {}
        self.results: List[Dict[str, Any]] = []
        logger.debug("PipelineService inicializado.")

    def run_pipeline(self, steps: List[PipelineStep]):
        logger.info("Ejecutando el pipeline completo.")
        self.results = []
        execution_order = 0

        for step in steps:
            step_name = step.name
            step_type = step.type
            step_params = step.parameters

            if not step_params:
                logger.error(f"No se encontraron parámetros para el paso '{step_name}'.")
                raise ValueError(f"Faltan parámetros para el paso '{step_name}'.")

            logger.info(f"Ejecutando paso: {step_name} (tipo: {step_type}, orden: {execution_order})")

            # Si el step es generation o verification, chequear si usan reference data. 
            # En el caso de que lo usen, sustituir adecuadamente los datos de referencia en el prompt guardados en reference_data_store
            # si step.uses_reference: 
                # Obtener reference data generado por los parse steps según orden de prioridad establecido en reference_step_names (primero se buscan los placeholders en el primero, sino en el segundo y así hasta el final)

                # En el caso de que sea reference data generado por un parse step, comprobar que el reference_step_number debe hacer referencia a un paso anteriormente ejecutado y que sea de tipo parse

                # Sustituirlo adecuadamente en lo prompt y system prompt (en caso de generate)

                # Sustituirlo adecuadamente en el prompt y system prompt para cada uno de los métodos (VerificationMethod)
                
                # Utilizar placeholder_service para sustituir los placeholders

            # si step.uses_verification: 
                # Ejecutar el step dependiendo de si el step.verification_status es el obtenido en el paso de verificación indicado
                # Sino, saltar al siguiente step

            # Generar el GenerateTextRequest, ParseRequest, o VerifyRequest

            # Correr el step y guardar resultados en results

            # En el caso de ser un parse step, guardar los resultados del parse también en reference_data_store

            # En el caso de que haya varios resultados generados (tanto en parse, como en generar), continuar con el pipeline para cada uno de ellos

            # Los resultados de un step pueden ser utilizados como input de un step siguiente:
                # GENERATE -> PARSE  : Para cada texto generado -> input de text para ParseRequest 
                # GENERATE -> VERIFY : Para cada texto generado -> parse automático que se queda con todo el texto -> placeholder automático a sustituir en prompt (si es necesario) de VerificationMethod
                # GENERATE -> GENERATE : Para cada texto generado -> parse automático que se queda con todo el texto -> placeholder automático a sustituir en prompt (si es necesario) de GenerateTextRequest
                # PARSE -> GENERATE : Para cada entrada de parse -> generar sustituyendo los placeholders (si es necesario) para prompt en GenerateTextRequest
                # PARSE -> VERIFY : Para cada entrada de parse -> verificar sustituyendo los placeholders (si es necesario) para prompt de VerificationMethod
                # PARSE -> PARSE : Para cada entrada de parse -> se puede hacer un nuevo parseo con nuevas reglas asociado a un nuevo step de un texto generado en un paso anterior o predeterminado
                # VERIFY -> GENERATE : resultado de verificación -> generar texto dependiendo de si la verificación ha tenido el resultado deseado (puede ser 'confirmed', 'review', or 'discarded')
                # VERIFY -> PARSE : resultado de verificación -> realizar el parse dependiendo de si la verificación ha tenido el resultado deseado (puede ser 'confirmed', 'review', or 'discarded')
                # VERIFY -> VERIFY : resultado de verificación -> realizar una nueva verificación dependiendo del resultado obtenido en la anterior

            # En el caso de que haya algún error al ejecutar el step, se imprime en pantalla y se salta al siguiente step. Si no hay más steps, se termina la ejecución y se devuelven los resultados obtenidos