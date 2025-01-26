import json
import os
from datetime import datetime

class FileRepository:
    @staticmethod
    def save(data: dict, output_dir: str, filename_prefix: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    
    