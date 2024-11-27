# utils/visualizer.py

import os
from typing import List
import matplotlib.pyplot as plt

class Visualizer:
    """
    Responsible for generating graphs and visualizing results.
    """

    @staticmethod
    def plot_threshold_vs_accuracy(thresholds: List[float], accuracies: List[float], output_dir: str = "out") -> None:
        """
        Plots Threshold vs. Precision and saves the figure to a file.

        Args:
            thresholds (List[float]): A list of threshold values.
            accuracies (List[float]): A list of accuracy values corresponding to the thresholds.
            output_dir (str, optional): Directory where the output image will be saved. Defaults to "out".

        Raises:
            Exception: If an error occurs during plotting or saving the figure.
        """
        try:
            # Ensure the output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Create the plot
            plt.figure(figsize=(10, 6))
            plt.plot(thresholds, accuracies, marker='o')
            plt.title('Threshold vs Precision')
            plt.xlabel('Threshold')
            plt.ylabel('Precision')
            plt.grid(True)

            # Save the figure
            filepath = os.path.join(output_dir, "threshold_vs_precision.png")
            plt.savefig(filepath)
            plt.close()
            print(f"Plot saved at {filepath}")

        except Exception as e:
            print(f"An error occurred while generating the plot: {e}")
            raise
