# application/use_cases/parsing/pipeline_use_case.py

from datetime import datetime
import os
import json
import logging
from typing import Dict, List
from app.domain.model.entities.pipeline import (
    PipelineRequest,
    PipelineResponse,
)
from app.domain.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

class PipelineUseCase:
    """
    PipelineUseCase orquesta una secuencia de pasos (generate, parse, verify)
    delegando cada paso al PipelineService. La salida de cada paso
    se convierte en la entrada para el siguiente paso.
    """

    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        Inicializa el PipelineUseCase con una instancia de PipelineService.

        Args:
            pipeline_service (PipelineService): El servicio que maneja los pasos del pipeline.
        """
        self.service = PipelineService(model_name)
        logger.debug("PipelineUseCase inicializado con PipelineService.")

    def execute(self, request: PipelineRequest) -> PipelineResponse:
        """
        Ejecuta el pipeline definido en 'request.steps'.
        Los outputs de un paso se convierten en inputs del siguiente.

        Args:
            request (PipelineRequest): La configuración del pipeline y datos.

        Returns:
            PipelineResponse: Los resultados agregados de todos los pasos.
        """

        logger.info("Iniciando la ejecución del pipeline...")

        try:
            # Inicializa reference_data_store con global_reference_data
            if request.global_references:
                self.service.global_references = request.global_references
                logger.debug("Datos de referencia globales cargados en PipelineService.")

            # Ejecuta el pipeline
            self.service.run_pipeline(request.steps)

            logger.info("Ejecución del pipeline finalizada.")
            serializable_results = self.service.get_results()

            # Devuelve los resultados completos del pipeline
            return PipelineResponse(
                step_results=serializable_results,
                verification_references={
                    'confirmed': self.service.confirmed_references,
                    'to_verify': self.service.to_verify_references
                }
            )

        except ValueError as e:
            logger.error(f"Error de validación al ejecutar el pipeline: {e}")
            raise  # Re-lanzar la excepción para que se capture en main.py
        except Exception as e:
            logger.error(f"Error al ejecutar el pipeline: {e}")
            raise  # Re-lanzar otras excepciones
