# cli.py

import inquirer
from main.main import main as execute_main
from config.config import *

class CLI:
    """
    Command Line Interface for the AutoAumento project.

    This class provides interactive menus for data generation and benchmarking,
    allowing users to select actions and configure parameters through a console interface.
    """

    def display_menu(self) -> None:
        """
        Displays the main menu to select execution options.
        """
        questions = [
            inquirer.List(
                "action",
                message="What action would you like to perform?",
                choices=[
                    "Data Generation",
                    "Evaluate Verification Model (Benchmark)",
                    "Exit"
                ],
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        action = answers["action"]
        if action == "Data Generation":
            self.handle_generation_menu()
        elif action == "Evaluate Verification Model (Benchmark)":
            self.handle_benchmark_menu()
        elif action == "Exit":
            print("Goodbye!")
            return

    # === Data Generation ===
    def handle_generation_menu(self) -> None:
        """
        Menu for data generation options.
        """
        questions = [
            inquirer.List(
                "action",
                message="Select data generation type",
                choices=[
                    "Normal Data Generation",
                    "Data Generation using Support JSON File"
                ],
            ),
            inquirer.List(
                "verification_method",
                message="Select verification method",
                choices=[
                    "All methods",
                    "LLM Consensus only",
                    "Semantic Sentence Similarity only"
                ],
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return
    
        
        verification_method = ""
        if answers["verification_method"] == "LLM Consensus":
            verification_method = "consensus"
        if answers["verification_method"] == "Semantic Sentence Similarity":
            verification_method = "embedding"
        if answers["verification_method"] == "Both":
            verification_method = "all"
            
        action = answers["action"]    
        if action == "Data Generation using Support JSON File":
            self.handle_generate_json(verification_method)
        elif action == "Normal Data Generation":
            self.handle_generate(verification_method)

    def handle_generate_json(self, verification_method: str) -> None:
        """
        Handles the generation of variations based on an existing dataset.
        """
        questions = [
            inquirer.Text(
                "data_file_path",
                message="Enter the name of the reference JSON data file (in /data directory)"
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        data_file = answers.get("data_file_path", None)

        try:
            execute_main(
                generate_from_dataset=True,
                verification_method=verification_method,
                data_file=data_file
            )
        except Exception as e:
            print(f"An error occurred during data generation: {e}")

    def handle_generate(self, verification_method: str) -> None:
        """
        Handles data generation without prior references.
        """
        try:
            execute_main(verification_method=verification_method)
        except Exception as e:
            print(f"An error occurred during data generation: {e}")

    # === Model Benchmark ===
    def handle_benchmark_menu(self) -> None:
        """
        Menu to handle the model benchmarking.
        """
        questions = [
            inquirer.List(
                "verification_method",
                message="Select the verification method",
                choices=[
                    "Semantic Distance between Embeddings",
                    "Consensus",
                    "Back"
                ],
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        method = answers["verification_method"]
        if method == "Semantic Distance between Embeddings":
            self.handle_embedding_benchmark()
        elif method == "Consensus":
            self.handle_consensus_benchmark()
        elif method == "Back":
            self.display_menu()
        else:
            print("Method not implemented yet.")

    def handle_embedding_benchmark(self) -> None:
        """
        Handles benchmarking using semantic distance between embeddings.
        """
        questions = [
            inquirer.List(
                "action",
                message="Select test type",
                choices=[
                    "Find Optimal Similarity Threshold",
                    "Evaluate a Specific Similarity Threshold",
                    "Back"
                ],
            ),
            inquirer.Text(
                "positive_label",
                message="Enter the label to evaluate positively (e.g., correct)"
            ),
            inquirer.Text(
                "data_file_path",
                message="Enter the name of the JSON data file to evaluate (in /data/ directory)"
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        action = answers["action"]
        positive_label = answers.get("positive_label")
        data_file_path = answers.get("data_file_path")

        if action == "Find Optimal Similarity Threshold":
            self.handle_find_optimal_threshold(positive_label, data_file_path)
        elif action == "Evaluate a Specific Similarity Threshold":
            self.handle_evaluate_with_threshold(positive_label, data_file_path)
        elif action == "Back":
            self.display_menu()

    def handle_find_optimal_threshold(self, positive_label: str, data_file_path: str) -> None:
        """
        Finds the optimal similarity threshold within a user-specified range.

        Args:
            positive_label (str): The label to consider as positive (e.g., 'correct').
            data_file_path (str): Path to the JSON data file for evaluation.
        """
        questions = [
            inquirer.Text(
                "min_threshold",
                message="Enter the minimum threshold to search for the optimal (e.g., 0.85)"
            ),
            inquirer.Text(
                "max_threshold",
                message="Enter the maximum threshold to search for the optimal (e.g., 0.95)"
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        min_threshold_str = answers.get("min_threshold")
        max_threshold_str = answers.get("max_threshold")

        if not _is_float(min_threshold_str) or not _is_float(max_threshold_str):
            print("Error: 'Minimum threshold' and 'Maximum threshold' values must be numbers.")
            return

        min_threshold = float(min_threshold_str)
        max_threshold = float(max_threshold_str)

        try:
            execute_main(
                benchmark=True,
                positive_label=positive_label,
                find_optimal_threshold=True,
                threshold_range=(min_threshold, max_threshold),
                verification_method="embedding",
                data_file=data_file_path
            )
        except Exception as e:
            print(f"An error occurred during the threshold search: {e}")

    def handle_evaluate_with_threshold(self, positive_label: str, data_file_path: str) -> None:
        """
        Evaluates a specific similarity threshold provided by the user.

        Args:
            positive_label (str): The label to consider as positive.
            data_file_path (str): Path to the JSON data file for evaluation.
        """
        questions = [
            inquirer.Text(
                "threshold",
                message="Enter the similarity threshold to use (e.g., 0.90)"
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        threshold_str = answers.get("threshold")
        if not _is_float(threshold_str):
            print("Error: The 'threshold' value must be numeric.")
            return

        threshold = float(threshold_str)

        try:
            execute_main(
                benchmark=True,
                positive_label=positive_label,
                threshold=threshold,
                verification_method="embedding",
                data_file=data_file_path
            )
        except Exception as e:
            print(f"An error occurred during threshold evaluation: {e}")

    def handle_consensus_benchmark(self) -> None:
        """
        Handles benchmarking using consensus methods.
        """
        questions = [
            inquirer.List(
                "consensus_method",
                message="Select the consensus method",
                choices=CONSENSUS_METHODS,
            ),
            inquirer.Text(
                "positive_label",
                message="Enter the label to evaluate positively (e.g., correct)"
            ),
            inquirer.Text(
                "data_file_path",
                message="Enter the name of the JSON data file to evaluate (in /data directory)"
            )
        ]
        answers = inquirer.prompt(questions)
        if not answers:
            print("Operation canceled.")
            return

        consensus_method = answers.get("consensus_method")
        positive_label = answers.get("positive_label")
        data_file_path = answers.get("data_file_path")
        
        if answers.get("consensus_method") == "semantic coherence" and data_file_path == "":
            data_file_path = "test-semantic-coherence.json"
        if answers.get("consensus_method") == "information loss" and data_file_path == "":
            data_file_path = "test-information-loss.json"
        if answers.get("consensus_method") == "redundant cohenrence" and data_file_path == "":
            data_file_path = "test.json"

        try:
            execute_main(
                benchmark=True,
                positive_label=positive_label,
                verification_method="consensus",
                consensus_method=consensus_method,
                data_file=data_file_path
            )
        except Exception as e:
            print(f"An error occurred during consensus benchmarking: {e}")


def _is_float(value: str) -> bool:
    """
    Checks if a value can be converted to a float.

    Args:
        value (str): The value to check.

    Returns:
        bool: True if the value can be converted to float, False otherwise.
    """
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


if __name__ == "__main__":
    cli = CLI()
    cli.display_menu()
