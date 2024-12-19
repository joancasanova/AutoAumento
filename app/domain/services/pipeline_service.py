# app/domain/services/pipeline_service.py

import logging
from typing import Any, Dict, List, Optional

from app.application.use_cases.generate_text_use_case import GenerateTextUseCase, GenerateTextRequest
from app.application.use_cases.parse_generated_output_use_case import ParseGeneratedOutputUseCase, ParseRequest
from app.application.use_cases.verify_use_case import VerifyUseCase, VerifyRequest
from app.domain.services.parse_service import ParseService
from app.domain.services.verifier_service import VerifierService
from app.infrastructure.external.llm.instruct_model import InstructModel

from app.domain.model.entities.generation import GeneratedResult
from app.domain.model.entities.parsing import ParseMode, ParseRule
from app.domain.model.entities.verification import (
    VerificationMethod,
    VerificationMode
)

logger = logging.getLogger(__name__)


class PipelineService:
    """
    PipelineService handles the sequential execution of steps in a pipeline.
    Each step can be 'generate', 'parse', or 'verify', and takes the
    output of the previous step as its input.

    This service returns a list of outputs for each step, suitable for
    continuing the pipeline or exporting intermediate data.
    """

    def __init__(self, llm: InstructModel):
        """
        Initializes the PipelineService with pre-instantiated LLM models for
        generate and verify steps to avoid multiple instantiations and excessive memory usage.

        Args:
            llm (InstructModel): Pre-instantiated LLM model for text generation.
        """
        self.llm = llm
        self.reference_data_store: Dict[str, Any] = {}
        # Initialize with global reference data if available
        # This will be set externally via PipelineUseCase
        logger.debug("PipelineService initialized with pre-instantiated LLM models.")

    def run_pipeline_step(
        self,
        step_type: str,
        params: Dict[str, Any],
        input_data: Any,
        step_number: int
    ) -> List[Any]:
        """
        Executes a single pipeline step of type 'generate', 'parse', or 'verify'.
        The output is always returned as a list of items to feed the next step.

        Args:
            step_type (str): 'generate', 'parse', or 'verify'.
            params (Dict[str, Any]): Parameters for the step.
            input_data (Any): Input data from the previous step.
            step_number (int): The current step number (1-based index).

        Returns:
            List[Any]: Output items from the step.
        """
        logger.info(f"Executing '{step_type}' step (Step {step_number}).")

        # Determine reference_data_source
        reference_data_source = params.get("reference_data_source", "global" if step_number == 1 else None)

        # Fetch reference_data based on source
        if reference_data_source == "global":
            if step_number != 1:
                logger.error("Global reference data can only be used in the first step.")
                raise ValueError("Global reference data can only be used in the first step.")
            reference_data = self.reference_data_store.get("global")
            if not reference_data:
                logger.error("Global reference data not provided.")
                raise ValueError("Global reference data not provided.")
        elif reference_data_source and reference_data_source.startswith("parse_step_"):
            try:
                parse_step_number = int(reference_data_source.split("_")[-1])
            except ValueError:
                logger.error(f"Invalid reference_data_source '{reference_data_source}'. Must be 'global' or 'parse_step_<number>'.")
                raise ValueError(f"Invalid reference_data_source '{reference_data_source}'. Must be 'global' or 'parse_step_<number>'.")
            if parse_step_number >= step_number:
                logger.error(f"Reference data source '{reference_data_source}' must refer to a parse step before the current step.")
                raise ValueError(f"Reference data source '{reference_data_source}' must refer to a parse step before the current step.")
            reference_data = self.reference_data_store.get(reference_data_source)
            if not reference_data:
                logger.error(f"Reference data '{reference_data_source}' not found.")
                raise ValueError(f"Reference data '{reference_data_source}' not found.")
        else:
            reference_data = None  # No reference data used

        # Execute the step based on its type
        if step_type == "generate":
            output_items = self._run_generate(params, reference_data, step_number)
        elif step_type == "parse":
            output_items = self._run_parse(params, input_data, step_number)
            # After a parse step, store its outputs as reference data for future steps
            self.reference_data_store[f"parse_step_{step_number}"] = output_items
        elif step_type == "verify":
            output_items = self._run_verify(params, input_data, reference_data, step_number)
        else:
            logger.warning(f"Unknown pipeline step type '{step_type}'. Skipping.")
            output_items = []

        logger.info(f"Step '{step_type}' completed. Outputs: {output_items}")
        return output_items

    def _run_generate(self, params: Dict[str, Any], reference_data: Optional[Dict[str, Any]]) -> List[str]:
        """
        Calls GenerateTextUseCase. Returns a list of generated strings
        (one string per generated sequence).

        Args:
            params (Dict[str, Any]): Parameters for the generate step.
            reference_data (Optional[Dict[str, Any]]): Reference data for placeholders.

        Returns:
            List[str]: Generated text sequences.
        """
        logger.info("Executing 'generate' step.")

        system_prompt = params["system_prompt"]
        user_prompt = params["user_prompt"]
        num_sequences = params.get("num_sequences", 1)
        max_tokens = params.get("max_tokens", 50)
        temperature = params.get("temperature", 1.0)

        # Utilize the pre-instantiated LLM model for generation
        generate_use_case = GenerateTextUseCase(self.llm)
        
        request = GenerateTextRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            num_sequences=num_sequences,
            max_tokens=max_tokens,
            temperature=temperature,
            reference_data=reference_data if reference_data else None
        )
        response = generate_use_case.execute(request)

        # response.generated_texts is a list[GeneratedResult]
        # Next step input: each .content is appended to a list
        outputs = [gen_result.content for gen_result in response.generated_texts]
        return outputs

    def _run_parse(self, params: Dict[str, Any], text_to_parse: str) -> List[Dict[str, str]]:
        """
        Calls ParseGeneratedOutputUseCase for the given input text.
        Returns a list of parse result entries (list of dicts).

        Args:
            params (Dict[str, Any]): Parameters for the parse step.
            input_item (Any): Input data from the previous step.

        Returns:
            List[Dict[str, str]]: Parsed entries.
        """
        logger.info("Executing 'parse' step.")

        # If the input is None or empty, skip
        if not text_to_parse:
            logger.warning("No input text provided for 'parse' step.")
            return []

        rules_file = params["rules_file"]
        output_filter = params.get("output_filter", "all")
        output_limit = params.get("output_limit")

        import json
        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load rules file '{rules_file}': {e}")
            raise

        # Convert each rule into a ParseRule object
        rules = []
        for rd in rules_data:
            try:
                mode = ParseMode(rd["mode"].lower())
                rule = ParseRule(
                    name=rd["name"],
                    pattern=rd["pattern"],
                    mode=mode,
                    secondary_pattern=rd.get("secondary_pattern"),
                    fallback_value=rd.get("fallback_value", None)
                )
                rules.append(rule)
            except KeyError as e:
                logger.error(f"Missing key in rules file: {e}")
                raise
            except ValueError as e:
                logger.error(f"Invalid mode in rules file: {e}")
                raise

        parse_service = ParseService()
        parse_use_case = ParseGeneratedOutputUseCase(parse_service)

        parse_request = ParseRequest(
            text=text_to_parse,
            rules=rules,
            output_filter=output_filter,
            output_limit=output_limit
        )
        parse_response = parse_use_case.execute(parse_request)

        # parse_response.parse_result.entries is List[Dict[str, str]]
        # These can be used as inputs for subsequent steps
        return parse_response.parse_result.entries

    def _run_verify(
        self,
        params: Dict[str, Any],
        input_item: Any,
        reference_data: Optional[Dict[str, Any]],
        step_number: int
    ) -> List[Dict[str, Any]]:
        """
        Calls VerifyUseCase. Returns a list with the final verification summary dict.
        In a pipeline with multiple inputs, each input item is verified separately.

        Args:
            params (Dict[str, Any]): Parameters for the verify step.
            input_item (Any): Input data from the previous step.
            reference_data (Optional[Dict[str, Any]]): Reference data for placeholders.
            step_number (int): Current step number.

        Returns:
            List[Dict[str, Any]]: Verification summaries.
        """
        logger.info("Executing 'verify' step.")

        # If there's no input, skip
        if input_item is None:
            logger.warning("No input item for 'verify' step.")
            return []

        methods_file = params["methods_file"]
        required_confirmed = params["required_confirmed"]
        required_review = params["required_review"]

        import json
        try:
            with open(methods_file, "r", encoding="utf-8") as f:
                methods_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load methods file '{methods_file}': {e}")
            raise

        methods_list = []
        for m in methods_data:
            try:
                mode = VerificationMode(m["mode"].upper())  # "ELIMINATORY" or "CUMULATIVE"
                verification_method = VerificationMethod(
                    mode=mode,
                    name=m["name"],
                    system_prompt=m["system_prompt"],
                    user_prompt=m["user_prompt"],
                    valid_responses=m["valid_responses"],
                    num_sequences=m.get("num_sequences", 3),
                    required_matches=m.get("required_matches", 2)
                )
                methods_list.append(verification_method)
            except KeyError as e:
                logger.error(f"Missing key in methods file: {e}")
                raise
            except ValueError as e:
                logger.error(f"Invalid mode in methods file: {e}")
                raise

        # Utilize the pre-instantiated LLM model for verification
        verifier_service = VerifierService(self.llm)
        verify_use_case = VerifyUseCase(verifier_service)

        verify_request = VerifyRequest(
            methods=methods_list,
            required_for_confirmed=required_confirmed,
            required_for_review=required_review,
            reference_data=reference_data if reference_data else None
        )
        verify_response = verify_use_case.execute(verify_request)

        # Return a short summary as a dict
        final_status = verify_response.verification_summary.final_status
        success_rate = verify_response.success_rate
        execution_time = verify_response.execution_time

        return [{
            "final_status": final_status,
            "success_rate": success_rate,
            "execution_time": execution_time
        }]
