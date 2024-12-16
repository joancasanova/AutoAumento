# domain/services/placeholder_service.py

import logging
import re
from typing import Dict, Set

logger = logging.getLogger(__name__)

class PlaceholderService:
    """
    Handles extraction and substitution of placeholders within prompt strings.
    Placeholders are denoted as '{placeholder_name}'.
    """

    @staticmethod
    def extract_placeholders(text: str) -> Set[str]:
        logger.debug("Extracting placeholders from text.")
        return set(re.findall(r"{([^{}]+)}", text))
    
    @staticmethod
    def validate_and_replace_placeholders(text: str, data: Dict[str, str]) -> str:
        logger.debug("Validating and replacing placeholders in text.")
        placeholders = PlaceholderService.extract_placeholders(text)
        
        for ph in placeholders:
            if ph not in data:
                logger.error(f"Placeholder '{ph}' not found in provided data.")
                raise ValueError(f"Placeholder '{ph}' not found in provided data")
            text = text.replace(f"{{{ph}}}", data[ph])
            
        return text
