# application/use_cases/benchmark_use_case.py

import logging
from datetime import datetime
from typing import Dict, List, Optional
from app.domain.model.entities.benchmark import BenchmarkConfig, BenchmarkEntry, BenchmarkMetrics, BenchmarkResult
from app.domain.services.benchmark_service import BenchmarkService

logger = logging.getLogger(__name__)

class BenchmarkUseCase:
    def __init__(self, model_name: str):
        self.benchmark_service = BenchmarkService(model_name)

    def run_benchmark(self, config: BenchmarkConfig, entries: List[BenchmarkEntry]):
        results = []
        
        for entry in entries:
            logger.debug(f"Running pipeline for entry: {entry.input_data}")
            pipeline_response = self.benchmark_service.execute_pipeline_for_entry(config, entry.input_data)

            logger.debug(pipeline_response)
            
            prediction = self._process_prediction(pipeline_response, entry)
            if prediction:
                results.append(prediction)

        metrics = self.benchmark_service.calculate_metrics(results, config.label_value)

        return metrics

    def _process_prediction(self, pipeline_response: Optional[Dict], entry: BenchmarkEntry) -> Optional[BenchmarkResult]:
        if not pipeline_response:
            logger.debug(f"Pipeline response is None for entry: {entry.input_data}")
            return None

        verify_step = next(
            (s for s in pipeline_response
             if s["step_type"] == "verify"),
            None
        )
        
        if not verify_step:
            return None

        if not verify_step["step_data"]:
            logger.debug(f"Verify step data is empty for entry: {entry.input_data}")
            return None
        
        step_data = verify_step.get("step_data", [])
        if not step_data:
            return None
        
        final_status = step_data[0].get("final_status", "").lower() # Access as dictionary now
        return BenchmarkResult(
            input_data=entry.input_data,
            predicted_label="confirmed" if final_status == "confirmed" else "not_confirmed",
            actual_label=entry.expected_label,
            timestamp=datetime.now()
        )