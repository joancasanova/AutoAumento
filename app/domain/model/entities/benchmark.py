# domain/model/entities/benchmark.py

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List
from domain.model.entities.pipeline import PipelineStep

@dataclass
class BenchmarkConfig:
    """
    Configuration parameters for benchmark execution.
    
    Attributes:
        model_name: Identifier for the ML model being evaluated
        pipeline_steps: Sequence of processing steps to evaluate
        label_key: Key to extract ground truth label from input data
        label_value: Expected value for positive classification
    """
    model_name: str
    pipeline_steps: List[PipelineStep]
    label_key: str
    label_value: str

@dataclass
class BenchmarkEntry:
    """
    Represents a single test case in the benchmark dataset.
    
    Attributes:
        input_data: Dictionary of input features/parameters
        expected_label: Ground truth label for validation
    """
    input_data: Dict[str, Any]
    expected_label: str

@dataclass
class BenchmarkResult:
    """
    Stores outcome of a single benchmark test case execution.
    
    Attributes:
        input_data: Original input data used for prediction
        predicted_label: Model-generated prediction
        actual_label: Ground truth label from dataset
        timestamp: Execution time of the test case
        
    Methods:
        to_dict: Serializes result for storage/transmission
    """
    input_data: Dict[str, Any]
    predicted_label: str
    actual_label: str
    timestamp: datetime

    def to_dict(self) -> dict:
        """Converts result to JSON-serializable dictionary format."""
        return {
            "input_data": self.input_data,
            "predicted_label": self.predicted_label,
            "actual_label": self.actual_label,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class BenchmarkMetrics:
    """
    Aggregated performance metrics from benchmark execution.
    
    Attributes:
        accuracy: Ratio of correct predictions to total cases
        precision: Ratio of true positives to all positive predictions
        recall: Ratio of true positives to all actual positives
        f1_score: Harmonic mean of precision and recall
        confusion_matrix: Breakdown of prediction outcomes with keys:
            - true_positive: Correct positive predictions
            - false_positive: Incorrect positive predictions
            - true_negative: Correct negative predictions
            - false_negative: Incorrect negative predictions
        misclassified: List of incorrectly predicted cases
        
    Methods:
        to_dict: Serializes metrics for reporting/analysis
    """
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: Dict[str, int]
    misclassified: List[BenchmarkResult]

    def to_dict(self) -> dict:
        """Converts metrics to analysis-ready dictionary format."""
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "confusion_matrix": self.confusion_matrix,
            "misclassified_count": len(self.misclassified)
        }