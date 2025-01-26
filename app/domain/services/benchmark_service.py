# domain/services/benchmark_service.py

import logging
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.domain.model.entities.benchmark import BenchmarkConfig, BenchmarkResult, BenchmarkMetrics
from app.domain.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)

class BenchmarkService:
    def __init__(self, model_name: str):
        self.pipeline_service = PipelineService(model_name)
        self.results: List[BenchmarkResult] = []

    def execute_pipeline_for_entry(self, config: BenchmarkConfig, entry: Dict) -> Optional[Dict]:
        try:
            self.pipeline_service.global_references = entry
            configured_steps = self._configure_steps(config.pipeline_steps, entry)
            self.pipeline_service.run_pipeline(configured_steps)
            return self.pipeline_service.get_results()
        except Exception as e:
            logger.error(f"Error ejecutando pipeline: {str(e)}")
            return None

    def _configure_steps(self, steps: List, entry: Dict) -> List:
        configured_steps = []
        for step in steps:
            cloned_step = deepcopy(step)
            self._substitute_placeholders(cloned_step.parameters, entry)
            configured_steps.append(cloned_step)
        return configured_steps

    def _substitute_placeholders(self, parameters: Any, data: Dict):
        if hasattr(parameters, 'system_prompt'):
            parameters.system_prompt = self._replace_in_template(parameters.system_prompt, data)
        if hasattr(parameters, 'user_prompt'):
            parameters.user_prompt = self._replace_in_template(parameters.user_prompt, data)
        if hasattr(parameters, 'text'):
            parameters.text = self._replace_in_template(parameters.text, data)

    def _replace_in_template(self, template: str, data: Dict) -> str:
        for key, value in data.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template

    def calculate_metrics(self, results: List[BenchmarkResult], label_value: str) -> BenchmarkMetrics:
        confusion_matrix = {
            "true_positive": 0,
            "false_positive": 0,
            "true_negative": 0,
            "false_negative": 0
        }
        misclassified = []
        
        for result in results:
            actual = result.actual_label
            predicted = result.predicted_label
            
            is_actual_positive = (actual == label_value)
            is_predicted_positive = (predicted == "confirmed")

            if is_actual_positive and is_predicted_positive:
                confusion_matrix["true_positive"] += 1
            elif not is_actual_positive and not is_predicted_positive:
                confusion_matrix["true_negative"] += 1
            elif is_actual_positive and not is_predicted_positive:
                confusion_matrix["false_negative"] += 1
                misclassified.append(result)
            else:
                confusion_matrix["false_positive"] += 1
                misclassified.append(result)

        total = len(results)

            
        # Manejar caso sin resultados
        if total == 0:
            return BenchmarkMetrics(
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                confusion_matrix=confusion_matrix,
                misclassified=misclassified
        )
        accuracy = (confusion_matrix["true_positive"] + confusion_matrix["true_negative"]) / total
        precision = confusion_matrix["true_positive"] / (confusion_matrix["true_positive"] + confusion_matrix["false_positive"] + 1e-10)
        recall = confusion_matrix["true_positive"] / (confusion_matrix["true_positive"] + confusion_matrix["false_negative"] + 1e-10)
        f1 = 2 * (precision * recall) / (precision + recall + 1e-10)

        return BenchmarkMetrics(
            accuracy=accuracy if total > 0 else 0.0,
            precision=precision if total > 0 else 0.0,
            recall=recall if total > 0 else 0.0,
            f1_score=f1,
            confusion_matrix=confusion_matrix,
            misclassified=misclassified
        )

    def save_misclassified(self, misclassified: List[BenchmarkResult]):
        filename = f"misclassified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([vars(result) for result in misclassified], f, indent=2, default=str)