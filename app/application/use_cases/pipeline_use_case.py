# application/use_cases/pipeline_use_case.py

import json
import logging
from datetime import datetime
from typing import List

from domain.model.entities.pipeline import PipelineRequest, PipelineResponse
from domain.services.pipeline_service import PipelineService
from infrastructure.file_repository import FileRepository

logger = logging.getLogger(__name__)

class PipelineUseCase:
    """
    Orchestrates pipeline execution and handles reference data processing.
    
    Responsibilities:
    - Manage complete pipeline lifecycle
    - Handle single and multi-reference executions
    - Coordinate result aggregation and storage
    - Maintain data consistency across executions
    """

    def __init__(self, 
                 generation_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct", 
                 verify_model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        Initializes pipeline components with model configurations.
        
        Args:
            generation_model_name: Model identifier for text generation
            verify_model_name: Model identifier for verification tasks
        """
        self.service = PipelineService(generation_model_name, verify_model_name)
        self.file_repo = FileRepository()
        logger.debug("Initialized PipelineUseCase with models: %s (gen), %s (verify)",
                    generation_model_name, verify_model_name)

    def _execute(self, request: PipelineRequest) -> PipelineResponse:
        """
        Executes a single pipeline run with provided configuration.
        
        Args:
            request: Pipeline configuration and input data
            
        Returns:
            PipelineResponse: Consolidated results from all steps
        """
        logger.info("Starting single pipeline execution")
        try:
            if request.global_references:
                logger.debug("Loading %d global references", len(request.global_references))
                self.service.global_references = request.global_references

            self.service.run_pipeline(request.steps)
            
            return PipelineResponse(
                step_results=self.service.get_results(),
                verification_references={
                    'confirmed': self.service.confirmed_references,
                    'to_verify': self.service.to_verify_references
                }
            )
            
        except Exception as e:
            logger.error("Pipeline execution failed: %s", str(e))
            raise

    def execute_with_references(self, 
                               request: PipelineRequest, 
                               reference_data_path: str) -> PipelineResponse:
        """
        Executes pipeline for multiple reference entries from a file.
        
        Args:
            request: Base pipeline configuration
            reference_data_path: Path to JSON file with reference entries
            
        Returns:
            PipelineResponse: Aggregated results from all executions
        """
        logger.info("Starting multi-reference pipeline execution")
        
        try:
            with open(reference_data_path, 'r') as f:
                reference_entries = json.load(f)
        except Exception as e:
            logger.error("Failed to load reference data: %s", str(e))
            raise

        cumulative_response = PipelineResponse(step_results=[], verification_references={'confirmed': [], 'to_verify': []})

        for idx, entry in enumerate(reference_entries):
            try:
                logger.debug("Processing reference entry %d/%d", idx+1, len(reference_entries))
                result = self._process_single_entry(request, entry)
                cumulative_response.step_results.extend(result.step_results)
                cumulative_response.verification_references['confirmed'].extend(result.verification_references['confirmed'])
                cumulative_response.verification_references['to_verify'].extend(result.verification_references['to_verify'])
                
                self._save_incremental_results(result)
                
            except Exception as e:
                logger.warning("Failed processing entry %d: %s", idx+1, str(e))
                continue

        return cumulative_response

    def _process_single_entry(self, 
                             base_request: PipelineRequest,
                             entry_data: dict) -> PipelineResponse:
        """
        Processes a single reference entry through the pipeline.
        
        Args:
            base_request: Original pipeline configuration
            entry_data: Specific reference data for this execution
            
        Returns:
            PipelineResponse: Results for this single entry
        """
        modified_request = PipelineRequest(
            steps=base_request.steps,
            global_references=entry_data
        )
        
        return self._execute(modified_request)

    def _save_incremental_results(self, response: PipelineResponse):
        """
        Appends results to persistent storage incrementally.
        
        Args:
            response: Pipeline results to append to files
        """
        try:
            # Main results
            self.file_repo.append(
                data=response.step_results,
                output_dir="out/pipeline/results",
                filename="pipeline_results.json"
            )
            
            # Verification results
            for result_type in ['confirmed', 'to_verify']:
                if response.verification_references[result_type]:
                    self.file_repo.append(
                        data=response.verification_references[result_type],
                        output_dir=f"out/pipeline/verification/{result_type}",
                        filename=f"{result_type}.json"
                    )
                    
        except Exception as e:
            logger.error("Failed saving incremental results: %s", str(e))
            raise