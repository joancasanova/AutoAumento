# app/application/use_cases/pipeline/pipeline_use_case.py

import logging
from typing import List, Any

from app.domain.model.entities.pipeline import (
    PipelineRequest,
    PipelineStep,
    PipelineStepResult,
    PipelineResponse
)
from app.domain.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


class PipelineUseCase:
    """
    PipelineUseCase orchestrates a sequence of steps (generate, parse, verify)
    by delegating each step to the PipelineService. The output of each step 
    becomes the input for the next step.
    """

    def __init__(self, pipeline_service: PipelineService):
        """
        Initializes the PipelineUseCase with a PipelineService instance.

        Args:
            pipeline_service (PipelineService): The service handling pipeline steps.
        """
        self.service = pipeline_service
        logger.debug("PipelineUseCase initialized with PipelineService.")

    def execute(self, request: PipelineRequest) -> PipelineResponse:
        """
        Executes the pipeline defined in 'request.steps'. For each step, 
        we take the outputs from the previous step as inputs to the next step.
        Returns a PipelineResponse with a list of results from all steps.

        Args:
            request (PipelineRequest): The pipeline configuration and data.

        Returns:
            PipelineResponse: Aggregated results of all pipeline steps.
        """

        logger.info("Starting pipeline execution...")

        step_results: List[PipelineStepResult] = []
        # Start with a single "input" item: None, meaning the first step might not require an explicit input
        current_inputs: List[Any] = [None]

        # Initialize reference_data_store with global_reference_data if provided
        if request.global_reference_data:
            self.service.reference_data_store["global"] = request.global_reference_data
            logger.debug("Global reference data loaded into PipelineService.")

        for idx, step in enumerate(request.steps, 1):
            logger.info(f"Executing pipeline step {idx}/{len(request.steps)}: {step.step_type}")

            next_inputs: List[Any] = []

            for input_item in current_inputs:
                try:
                    # Run the step and get outputs
                    output_items = self.service.run_pipeline_step(
                        step_type=step.step_type,
                        params=step.params,
                        input_data=input_item,
                        step_number=idx
                    )
                except Exception as e:
                    logger.error(f"Error executing step {idx} ('{step.step_type}'): {e}")
                    raise

                # Record the step result
                step_result = PipelineStepResult(
                    step_type=step.step_type,
                    input_data=input_item,
                    output_data=output_items
                )
                step_results.append(step_result)

                # Append new items to next_inputs for the next step
                if isinstance(output_items, list):
                    next_inputs.extend(output_items)
                else:
                    next_inputs.append(output_items)

            # The outputs collected become the inputs for the next step
            current_inputs = next_inputs

        logger.info("Pipeline execution finished.")
        response = PipelineResponse(step_results=step_results)
        return response
