# application/use_cases/parsing/parse_generated_output_use_case.py

import logging
from domain.model.entities.parsing import ParseRequest, ParseResponse, ParseRule
from domain.services.parse_service import ParseService

logger = logging.getLogger(__name__)

class ParseRequestValidationError(Exception):
    """
    Custom exception to indicate invalid parse request parameters.
    """
    pass

class ParseUseCase:
    """
    Use case that parses text according to a set of rules (ParseRule objects).
    It also supports filtering the parsed output (e.g., keep only successful parse entries).
    """
    def __init__(self):
        """
        Constructor requires an instance of ParseService which encapsulates 
        the text parsing logic (regex, keyword scanning, etc.).
        """
        self.parse_service = ParseService()

    def execute(self, request: ParseRequest) -> ParseResponse:
        """
        Execute the parse workflow:
         1) Validate the request input (text, rules).
         2) Parse the text using the parse service.
         3) Filter the parsed results based on requested criteria.
         4) Return a ParseResponse object containing the final parse result.
        """
        logger.info("Executing ParseGeneratedOutputUseCase")
        try:
            self._validate_request(request)
        except ValueError as e:
            logger.error(f"Invalid parse request: {e}")
            raise ParseRequestValidationError(f"Invalid parse request: {e}")

        try:
            logger.debug("Parsing the provided text with specified rules.")
            parse_result = self.parse_service.parse_text(
                text=request.text,
                rules=request.rules
            )
            logger.debug("Filtering parse results as per request output filter.")
            filtered_result = self.parse_service.filter_entries(
                parse_result,
                request.output_filter,
                request.output_limit,
                request.rules
            )

            logger.info(f"Parsed {len(filtered_result.entries)} entry/entries successfully.")
            return ParseResponse(
                parse_result=filtered_result
            )

        except Exception as e:
            logger.exception("Error during parsing.")
            raise e

    def _validate_request(self, request: ParseRequest) -> None:
        """
        Checks basic validity:
         - Text should not be empty.
         - The rules list must not be empty.
         - Each rule must have a pattern.
        """
        if not request.text.strip():
            raise ValueError("Text cannot be empty or whitespace.")
        if not request.rules:
            raise ValueError("Rules list cannot be empty.")
        for rule in request.rules:
            if not rule.pattern:
                raise ValueError(f"Rule '{rule.name}' must have a pattern.")
