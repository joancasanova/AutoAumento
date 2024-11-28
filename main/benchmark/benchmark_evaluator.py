# benchmark/benchmarker.py

from collections import defaultdict
from typing import List, Dict, Tuple, Callable, Any, Optional

from main.utils.visualizer import Visualizer
from main.benchmark.result_handler import ResultHandler

class BenchmarkEvaluator:
    """
    Responsible for evaluating models and calculating metrics based on predictions.
    """

    def __init__(self, verifier, data: List[Dict[str, Any]], positive_label: str):
        """
        Initializes the BenchmarkEvaluator.

        Args:
            verifier: An instance of the Verifier class.
            data (List[Dict[str, Any]]): The dataset to evaluate.
            positive_label (str): The label considered as positive in the evaluation.
        """
        self.verifier = verifier
        self.data = data
        self.positive_label = positive_label

    def evaluate(self, evaluation_function: Callable, **kwargs) -> float:
        """
        Evaluates the model using the provided evaluation function.

        Args:
            evaluation_function (Callable): The function used to evaluate each data point.
            **kwargs: Additional keyword arguments for the evaluation function.

        Returns:
            float: The overall accuracy of the model.
        """
        correct_predictions = defaultdict(int)
        total_predictions = defaultdict(int)
        misclassified_cases = []
        positive_label_found = False

        for datapoint in self.data:
            input_text = datapoint.get('input')
            output_text = datapoint.get('output')
            label = datapoint.get('label')

            # Map the current label to classes
            actual_class = self._map_labels_to_classes(label)
            if actual_class == "positive":
                positive_label_found = True

            try:
                # Evaluate the datapoint
                prediction = evaluation_function(input_text, output_text, **kwargs)
            except Exception as e:
                error_msg = f"evaluation -> {e}"
                raise ValueError(error_msg)
            
            # Determine the predicted class
            predicted_class = 'positive' if prediction else 'negative'

            # Update counts
            total_predictions[label] += 1
            if predicted_class == actual_class:
                correct_predictions[label] += 1
            else:
                # Save misclassified case
                misclassified_cases.append({
                    'input': input_text,
                    'output': output_text,
                    'actual_class': actual_class,
                    'predicted': predicted_class
                })

        if not positive_label_found:
            print(f"The selected positive label was not found in the dataset.\nSelected label: {self.positive_label}")

        # Calculate accuracy per label
        accuracy_per_label = {
            label: (correct_predictions[label] / total_predictions[label]) if total_predictions[label] > 0 else 0
            for label in total_predictions
        }

        # Calculate overall accuracy
        total_correct = sum(correct_predictions.values())
        total = sum(total_predictions.values())
        overall_accuracy = (total_correct / total) if total > 0 else 0

        # Log results
        print(f"Overall accuracy: {overall_accuracy:.2%}")
        for label, accuracy in accuracy_per_label.items():
            print(f"- Accuracy for '{label}': {accuracy:.2%}")

        # Save misclassified cases
        try:
            ResultHandler.save_misclassified_cases(misclassified_cases)
        except Exception as e:
            error_msg = f"An error occurred while saving misclassified cases: {e}"
            raise ValueError(error_msg)

        return overall_accuracy

    def find_optimal_similarity_threshold(self, threshold_range: Tuple[float, float]) -> Tuple[Optional[float], float, List[float], List[float]]:
        """
        Finds the optimal threshold for semantic similarity.

        Args:
            threshold_range (Tuple[float, float]): A tuple containing the minimum and maximum thresholds to search.

        Returns:
            Tuple[Optional[float], float, List[float], List[float]]:
                - The best threshold found.
                - The best accuracy achieved.
                - List of thresholds tested.
                - List of corresponding accuracies.

        Raises:
            ValueError: If an invalid threshold range is provided.
        """
        if not threshold_range or len(threshold_range) != 2:
            raise ValueError("A valid range (min, max) is required to search for the optimal threshold.")

        min_threshold, max_threshold = threshold_range
        best_threshold = None
        best_accuracy = 0.0
        thresholds = []
        accuracies = []

        current_threshold = min_threshold
        while current_threshold <= max_threshold:
            try:
                overall_accuracy = self.evaluate(
                    self.verifier.is_similar,
                    threshold=current_threshold
                )
            except Exception as e:
                error_msg = f"evaluation at threshold {current_threshold} -> {e}"
                raise ValueError(error_msg)

            thresholds.append(current_threshold)
            accuracies.append(overall_accuracy)
            if overall_accuracy > best_accuracy:
                best_accuracy = overall_accuracy
                best_threshold = current_threshold
            current_threshold += 0.01

        print(f"\nOptimal threshold found: {best_threshold:.2f} with overall accuracy of {best_accuracy:.2%}")
        try:
            Visualizer.plot_threshold_vs_accuracy(thresholds, accuracies)
        except Exception as e:
            error_msg = f"An error occurred while plotting thresholds vs accuracies: {e}"
            
            raise ValueError(error_msg)

        return best_threshold, best_accuracy, thresholds, accuracies

    def _map_labels_to_classes(self, label: str) -> str:
        """
        Maps labels to classes ('positive' or 'negative') based on the specified positive label.

        Args:
            label (str): The label to map.

        Returns:
            str: 'positive' if the label matches the positive_label, 'negative' otherwise.
        """
        return 'positive' if label == self.positive_label else 'negative'
