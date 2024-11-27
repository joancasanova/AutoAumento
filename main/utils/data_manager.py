# utils/data_manager.py

import json
from typing import List, Dict, Any

class DataManager:
    """
    Responsible for loading and saving data to and from JSON files.
    """

    @staticmethod
    def load_json(file_name: str, description: str) -> List[Dict[str, Any]]:
        """
        Loads a JSON file from disk.

        Args:
            file_name (str): Path to the JSON file.
            description (str): Description of the file (for logging).

        Returns:
            List[Dict[str, Any]]: Contents of the JSON file if loaded successfully.

        Raises:
            FileNotFoundError: If the file is not found.
            ValueError: If the JSON file is invalid or missing mandatory keys.
            Exception: For any other exceptions that occur during loading.
        """
        try:
            with open(file_name, "r") as file:
                data = json.load(file)

            # Verify that data is a list of dictionaries
            if not isinstance(data, list):
                raise ValueError(f"Expected data to be a list, got {type(data)}")

            print(f"{description} loaded successfully from {file_name}.")
            return data

        except FileNotFoundError as e:
            print(f"File not found: {file_name}")
            raise e

        except json.JSONDecodeError as e:
            print(f"Error loading {description} from {file_name}: Invalid JSON format.")
            raise ValueError(f"Invalid JSON format in file {file_name}") from e

        except Exception as e:
            print(f"Error loading {description}: {e}")
            raise e

    @staticmethod
    def register_data(
        valid_generations: List[Dict[str, Any]],
        to_verify_data: List[Dict[str, Any]],
        confirmed_file_name: str,
        verify_file_name: str
    ) -> None:
        """
        Registers data in the corresponding files for confirmed and to-be-verified data.

        Args:
            valid_generations (List[Dict[str, Any]]): Valid data to be directly confirmed.
            to_verify_data (List[Dict[str, Any]]): Data that needs verification.
            confirmed_file_name (str): Path to the confirmed data file.
            verify_file_name (str): Path to the verification data file.
        """
        try:
            # Load existing data from files
            confirmed_data = []
            verify_data = []

            # Load confirmed data if the file exists
            try:
                confirmed_data = DataManager.load_json(confirmed_file_name, "Confirmed data")
            except FileNotFoundError:
                print(f"Confirmed data file not found. A new one will be created at {confirmed_file_name}.")

            # Load verification data if the file exists
            try:
                verify_data = DataManager.load_json(verify_file_name, "Verification data")
            except FileNotFoundError:
                print(f"Verification data file not found. A new one will be created at {verify_file_name}.")

            # Add new entries to existing data
            if valid_generations:
                confirmed_data.extend(valid_generations)
                print(f"Added {len(valid_generations)} entries to confirmed data.")

            if to_verify_data:
                verify_data.extend(to_verify_data)
                print(f"Added {len(to_verify_data)} entries to verification data.")

            # Save the updated data back to the files
            with open(confirmed_file_name, "w") as file:
                json.dump(confirmed_data, file, indent=4)
                print(f"Confirmed data saved to {confirmed_file_name}.")

            with open(verify_file_name, "w") as file:
                json.dump(verify_data, file, indent=4)
                print(f"Verification data saved to {verify_file_name}.")

        except Exception as e:
            print(f"Error registering data: {e}")
            raise e
