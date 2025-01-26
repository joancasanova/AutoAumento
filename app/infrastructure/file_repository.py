# infrastructure/file_repository.py

import json
import os
from datetime import datetime
from typing import Any, Union

class FileRepository:
    """
    Handles file system operations for data persistence.
    
    Provides methods for saving data with timestamped filenames
    and appending data to existing files.
    """

    @staticmethod
    def save(data: dict, output_dir: str, filename_prefix: str) -> str:
        """
        Saves data to a new timestamped JSON file.
        
        Args:
            data: Dictionary containing data to save
            output_dir: Target directory for the file
            filename_prefix: Base name for the file (timestamp will be added)
            
        Returns:
            str: Full path to the created file
            
        Example:
            save(data, "results", "experiment") -> "results/experiment_20230101_123456.json"
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        return filepath
    
    @staticmethod
    def append(data: Any, output_dir: str, filename: str) -> str:
        """
        Appends data to an existing JSON file or creates a new one.
        
        Handles:
        - Creating directories if needed
        - Initializing empty files
        - Converting existing content to list format
        - Maintaining JSON integrity
        
        Args:
            data: Data to append (any JSON-serializable type)
            output_dir: Target directory for the file
            filename: Exact filename to use (no timestamp)
            
        Returns:
            str: Full path to the modified file
            
        Raises:
            JSONDecodeError: If existing file contains invalid JSON
        """
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        existing_data = []
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []

        # Ensure we're working with a list to enable appending
        if not isinstance(existing_data, list):
            existing_data = [existing_data]
            
        existing_data.append(data)
        
        # Atomic write operation
        with open(filepath, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)
            
        return filepath