# benchmark/result_handler.py

import json
import os
from typing import List, Dict

class ResultHandler:
    """
    Responsible for saving results and reports in different formats.
    """

    @staticmethod
    def save_misclassified_cases(
        misclassified_cases: List[Dict],
        filepath: str = "out/misclassified_cases.json"
    ) -> None:
        """
        Saves misclassified cases to a JSON file.

        Args:
            misclassified_cases (List[Dict]): A list of misclassified cases to save.
            filepath (str, optional): The file path where the misclassified cases will be saved.
                Defaults to "out/misclassified_cases.json".

        Raises:
            Exception: If an error occurs while saving the file.
        """
        if misclassified_cases:
            try:
                # Ensure the output directory exists
                output_dir = os.path.dirname(filepath)
                os.makedirs(output_dir, exist_ok=True)

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(misclassified_cases, f, ensure_ascii=False, indent=4)
                print(f"Misclassified cases saved to: {filepath}")
            except Exception as e:
                print(f"while saving misclassified cases -> {e}")
                raise e
        else:
            print("No misclassified cases to save.")
