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
            prediction = self._process_prediction(pipeline_response, entry)
            if prediction:
                results.append(prediction)

        metrics = self.benchmark_service.calculate_metrics(results, config.label_value)
        self._display_results(metrics)

        if metrics.misclassified: # Save misclassified only if there are any
            self.benchmark_service.save_misclassified(metrics.misclassified)
        else:
            logger.info("No misclassified entries to save.")

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

    def _display_results(self, metrics: BenchmarkMetrics):
        print("\n=== Resultados del Benchmark ===")
        print(f"• Exactitud (Accuracy): {metrics.accuracy:.2%}")
        print(f"• Precisión: {metrics.precision:.2%}")
        print(f"• Sensibilidad (Recall): {metrics.recall:.2%}")
        print(f"• F1-Score: {metrics.f1_score:.2%}")
        print("\nMatriz de Confusión:")
        print(f"Verdaderos Positivos: {metrics.confusion_matrix['true_positive']}")
        print(f"Falsos Positivos: {metrics.confusion_matrix['false_positive']}")
        print(f"Verdaderos Negativos: {metrics.confusion_matrix['true_negative']}")
        print(f"Falsos Negativos: {metrics.confusion_matrix['false_negative']}")
        print(f"Total de casos evaluados: {len(metrics.misclassified) + metrics.confusion_matrix['true_positive'] + metrics.confusion_matrix['false_positive'] + metrics.confusion_matrix['true_negative']}")
        print(f"\nCasos mal clasificados guardados en: misclassified_*.json")