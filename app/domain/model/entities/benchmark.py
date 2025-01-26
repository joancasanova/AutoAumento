# domain/model/entities/benchmark.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
from app.domain.model.entities.pipeline import PipelineStep

@dataclass
class BenchmarkConfig:
    model_name: str
    pipeline_steps: List[PipelineStep]
    label_key: str
    label_value: str

@dataclass
class BenchmarkEntry:
    input_data: Dict[str, Any]
    expected_label: str

@dataclass
class BenchmarkResult:
    input_data: Dict[str, Any]
    predicted_label: str
    actual_label: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "input_data": self.input_data,
            "predicted_label": self.predicted_label,
            "actual_label": self.actual_label,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class BenchmarkMetrics:
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: Dict[str, int]
    misclassified: List[BenchmarkResult]

    def to_dict(self) -> dict:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "confusion_matrix": self.confusion_matrix,
            "misclassified_count": len(self.misclassified)
        }