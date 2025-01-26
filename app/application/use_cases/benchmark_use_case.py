# application/use_cases/benchmark_use_case.py

import logging
from datetime import datetime
from typing import Dict, List, Optional
from domain.model.entities.benchmark import BenchmarkConfig, BenchmarkEntry, BenchmarkMetrics, BenchmarkResult
from domain.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)

class BenchmarkUseCase:
    """
    Coordinates the benchmarking process for evaluating pipeline performance.
    
    Responsibilities:
    - Executes the pipeline for each benchmark entry
    - Processes pipeline responses to extract predictions
    - Calculates performance metrics based on results
    """
    
    def __init__(self, model_name: str):
        """Initializes the use case with required services.
        
        Args:
            model_name: Identifier for the ML model to benchmark
        """
        self.benchmark_service = BenchmarkService(model_name)

    def run_benchmark(self, config: BenchmarkConfig, entries: List[BenchmarkEntry]) -> BenchmarkMetrics:
        """Executes the full benchmarking workflow.
        
        Args:
            config: Benchmark configuration parameters
            entries: List of input entries with expected labels
            
        Returns:
            BenchmarkMetrics: Calculated performance metrics
        """
        results = []
        
        # Process each benchmark entry through the pipeline
        for entry in entries:
            logger.debug(f"Running pipeline for entry: {entry.input_data}")
            
            # Execute pipeline and get response
            pipeline_response = self.benchmark_service.execute_pipeline_for_entry(config, entry.input_data)
            logger.debug(pipeline_response)
            
            # Extract prediction from pipeline response
            prediction = self._process_prediction(pipeline_response, entry)
            if prediction:
                results.append(prediction)

        # Calculate final performance metrics
        return self.benchmark_service.calculate_metrics(results, config.label_value)

    def _process_prediction(self, pipeline_response: Optional[Dict], entry: BenchmarkEntry) -> Optional[BenchmarkResult]:
        """Extracts prediction from pipeline response and validates results.
        
        Args:
            pipeline_response: Raw output from pipeline execution
            entry: Original benchmark entry with expected label
            
        Returns:
            BenchmarkResult if valid prediction found, None otherwise
        """
        # Handle empty pipeline response
        if not pipeline_response:
            logger.debug(f"Pipeline response is None for entry: {entry.input_data}")
            return None

        # Find verification step in pipeline results
        verify_step = next(
            (s for s in pipeline_response
             if s["step_type"] == "verify"),
            None
        )
        
        # Validate verification step existence
        if not verify_step:
            return None

        # Check for valid step data
        if not verify_step["step_data"]:
            logger.debug(f"Verify step data is empty for entry: {entry.input_data}")
            return None
        
        # Extract final verification status
        step_data = verify_step.get("step_data", [])
        if not step_data:
            return None
        
        # Determine prediction based on verification outcome
        final_status = step_data[0].get("final_status", "").lower()
        return BenchmarkResult(
            input_data=entry.input_data,
            predicted_label="confirmed" if final_status == "confirmed" else "not_confirmed",
            actual_label=entry.expected_label,
            timestamp=datetime.now()
        )