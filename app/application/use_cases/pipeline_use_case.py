# app/application/use_cases/pipeline/pipeline_use_case.py

import logging
from typing import List, Any, Dict

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

    def __init__(self, pipeline_service: PipelineService):
        """
        Inicializa el PipelineUseCase con una instancia de PipelineService.

        Args:
            pipeline_service (PipelineService): El servicio que maneja los pasos del pipeline.
        """
        self.service = pipeline_service
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
            if request.global_reference_data:
                self.service.reference_data_store["global"] = request.global_reference_data
                logger.debug("Datos de referencia globales cargados en PipelineService.")

            # Ejecuta el pipeline
            self.service.run_pipeline(request.steps, request.parameters)

            logger.info("Ejecución del pipeline finalizada.")

            # Devuelve los resultados completos del pipeline
            return PipelineResponse(
                step_results=self.service.get_intermediate_results()
            )

        except Exception as e:
            logger.error(f"Error al ejecutar el pipeline: {e}")
            raise