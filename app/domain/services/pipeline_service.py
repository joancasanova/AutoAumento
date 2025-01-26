from typing import Any, Dict, List, Optional, Set, Tuple
import re
import logging
from datetime import datetime
from copy import deepcopy
import itertools

from app.domain.model.entities.pipeline import PipelineStep
from app.domain.model.entities.generation import GenerateTextRequest, GeneratedResult
from app.domain.model.entities.parsing import ParseRequest, ParseResult, ParseRule, ParseMode
from app.domain.model.entities.verification import VerificationMethod, VerificationSummary, VerifyRequest

from app.domain.services.parse_service import ParseService
from app.domain.services.verifier_service import VerifierService
from app.domain.services.generate_service import GenerateService

logger = logging.getLogger(__name__)

class PlaceholderDict(dict):
    """
    A custom dictionary that returns the placeholder itself if a key is not found.
    For example, if the key 'name' is not in the dictionary, it will return '{name}'.
    """
    def __missing__(self, key):
        return f"{{{key}}}"

class PipelineService:
    """
    Manages the execution of a pipeline, processing a sequence of steps (PipelineStep) 
    and storing their results. It integrates parsing, generation, and verification services.
    """

    def __init__(self, model_name: str):
        """
        Initializes the PipelineService with parsing, generation, and verification services.

        Args:
            model_name: The name of the language model to be used for text generation.
        """
        self.parse_service = ParseService()
        self.generate_service = GenerateService(model_name)
        self.verifier_service = VerifierService(self.generate_service)

        self.results: List[Optional[Tuple[str, List[Any]]]] = []  # Stores results of each step: (step_type, list_of_results)
        self.global_references: Dict[str, str] = {}  # Global references usable across all steps

    def run_pipeline(self, steps: List[PipelineStep]) -> None:
        """
        Executes the pipeline by processing each step sequentially.

        Args:
            steps: A list of PipelineStep objects defining the pipeline's steps.
        """
        self.results = []  # Clear previous results
        try:
            for step_number, step in enumerate(steps):
                self._validate_step_references(step, step_number)
                step_result = self._execute_step(step, step_number)
                self._store_result(step_number, step.type, step_result)
        except Exception as e:
            logger.error(f"Pipeline execution failed at step {step_number}: {str(e)}")
            raise

    def get_results(self) -> List[Dict]:
        """
        Returns the accumulated results of all executed steps.
        """

        # Convert results to a serializable format
        serializable_results = []
        for result in self.results:
            step_type, step_data = result
                
            # Convertimos los datos del paso a una lista de diccionarios
            step_data_dicts = [
                item.to_dict() if hasattr(item, 'to_dict') else item
                for item in step_data
            ]

            serializable_results.append({
                "step_type": step_type,
                "step_data": step_data_dicts
            })

        return serializable_results
    
    def _validate_step_references(self, step: PipelineStep, step_number: int) -> None:
        """
        Validates that the reference_step_numbers for a step are valid (exist and are before current step).

        Args:
            step: The PipelineStep object being validated.
            step_number: The index of the current step.

        Raises:
            ValueError: If any reference is invalid.
        """
        if step.uses_reference:
             if not step.reference_step_numbers and not self.global_references:
                 raise ValueError(f"Step {step_number} uses references but no references are provided.")
             for ref_index in step.reference_step_numbers:
                if not (0 <= ref_index < step_number):
                   raise ValueError(f"Step {step_number} has an invalid reference to step {ref_index}. Must be a previous step.")

    def _execute_step(self, step: PipelineStep, step_number: int) -> List[Any]:
        """
        Executes the logic for a single pipeline step.

        Handles reference and verification checks. Returns an empty list if validations fail.

        Args:
            step: The PipelineStep object defining the current step.
            step_number: The index of the current step.

        Returns:
            A list of results from the step, or an empty list if validations fail.
        """
        if step.uses_reference and not self._validate_references(step.reference_step_numbers, step_number):
            return []
        
        if step.type == "generate":
            return self._execute_generate(step, step_number)
        elif step.type == "parse":
            return self._execute_parse(step, step_number)
        elif step.type == "verify":
            return self._execute_verify(step, step_number)
        else:
            logger.warning(f"Unknown step type: {step.type}")
            return []

    def _store_result(self, step_number: int, step_type: str, step_result: List[Any]) -> None:
        """
        Stores the results of a step in the `self.results` list.

        Args:
            step_number: The index of the current step.
            step_type: The type of the step (e.g., 'generate', 'parse', 'verify').
            step_result: The list of results from the step.
        """
        while len(self.results) <= step_number:
            self.results.append(None)

        if self.results[step_number] is None:
            self.results[step_number] = (step_type, step_result)
        else:
            _, existing_results = self.results[step_number]
            existing_results.extend(step_result)

    def _validate_references(self, reference_step_numbers: List[int], current_step_number: int) -> bool:
        """
        Checks if the referenced steps have valid results and are before the current step.

        Args:
            reference_step_numbers: A list of indices of steps being referenced.
            current_step_number: The index of the current step.

        Returns:
            True if all references are valid, False otherwise.
        """
        for ref_index in reference_step_numbers:
            if not (0 <= ref_index < current_step_number and ref_index < len(self.results) and self.results[ref_index]):
                return False
        return True

    def _execute_generate(self, step: PipelineStep, step_number: int) -> List[GeneratedResult]:
        """
        Executes a 'generate' step, handling prompt variations based on references.

        Args:
            step: The PipelineStep object for the generate step.
            step_number: The index of the current step.

        Returns:
            A list of GeneratedResult objects.
        """
        request: GenerateTextRequest = step.parameters

        if not step.uses_reference:
            # Execute without references
            return self.generate_service.generate(**request.dict())

        reference_data = self._get_reference_data(step.reference_step_numbers, step_number)

        prompt_variations = self._create_prompt_variations(request, reference_data)

        all_results = []
        for system_prompt, user_prompt, reference_dict in prompt_variations:
            results = self.generate_service.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                num_sequences=request.num_sequences,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            for result in results:
                result.reference_data = reference_dict
            all_results.extend(results)

        return all_results

    def _execute_parse(self, step: PipelineStep, step_number: int) -> List[ParseResult]:
        """
        Executes a 'parse' step.

        Args:
            step: The PipelineStep object for the parse step.
            step_number: The index of the current step.

        Returns:
            A list containing the ParseResult.
        """
        request: ParseRequest = step.parameters
        
        if not step.uses_reference:
            parse_result = self.parse_service.parse_text(
                text=request.text,
                rules=request.rules
            )

            filtered_parse_result = self.parse_service.filter_entries(
                parse_result=parse_result,
                filter_type=request.output_filter,
                n=request.output_limit,
                rules=request.rules
            )

            return [filtered_parse_result]
    
        reference_data = self._get_reference_data(step.reference_step_numbers, step_number)
        
        parse_results = []
        for _, step_type, step_results in reference_data: 
            if step_type == "generate":
                generated_result: GeneratedResult
                for generated_result in step_results:
                    text = generated_result.content
                    parse_result = self.parse_service.parse_text(
                        text=text,
                        rules=request.rules
                    )

                    filtered_parse_result = self.parse_service.filter_entries(
                        parse_result=parse_result,
                        filter_type=request.output_filter,
                        n=request.output_limit,
                        rules=request.rules
                    )
                    parse_results.append(filtered_parse_result)

        return parse_results


    def _execute_verify(self, step: PipelineStep, step_number: int) -> List[VerificationSummary]:
        """
        Executes a 'verify' step, handling method variations based on references.

        Args:
            step: The PipelineStep object for the verify step.
            step_number: The index of the current step.

        Returns:
            A list of VerificationSummary objects.
        """
        request: VerifyRequest = step.parameters

        if not step.uses_reference:
            verification_summary = self.verifier_service.verify(
                methods=request.methods,
                required_for_confirmed=request.required_for_confirmed,
                required_for_review=request.required_for_review
            )
            return [verification_summary]

        reference_data = self._get_reference_data(step.reference_step_numbers, step_number)

        verify_requests_variations = self._create_methods_variations(request, reference_data)

        all_results = []
        for verify_request, reference_dict in verify_requests_variations:
            result = self.verifier_service.verify(
                methods=verify_request.methods,
                required_for_confirmed=verify_request.required_for_confirmed,
                required_for_review=verify_request.required_for_review
            )
            result.reference_data = reference_dict
            all_results.append(result)
        
        return all_results
    
    def _create_methods_variations(
        self,
        original_request: VerifyRequest,
        reference_data: List[Tuple[int, str, List[Any]]]
    ) -> List[Tuple[VerifyRequest, Dict[str, str]]]:
        """
        Generates variations of VerifyRequests by combining variations of VerificationMethods.

        Args:
            original_request: The original VerifyRequest.
            reference_data: Data from referenced steps.

        Returns:
            A list of tuples, each containing a new VerifyRequest with method variations and its reference data.
        """
        new_requests = []

        # Generate variations for each method
        methods_variations = [
            self._generate_variations(
                method.system_prompt,
                method.user_prompt,
                reference_data,
                {
                    "mode": method.mode,
                    "name": method.name,
                    "num_sequences": method.num_sequences,
                    "valid_responses": method.valid_responses,
                    "required_matches": method.required_matches,
                    "max_tokens": method.max_tokens,
                    "temperature": method.temperature
                }
            )
            for method in original_request.methods
        ]

        # Combine method variations using itertools.product
        for combination in itertools.product(*methods_variations):
            new_methods = []
            combined_reference_dict = {}
            for method_variation, reference_dict in combination:
                new_methods.append(method_variation)
                combined_reference_dict.update(reference_dict)

            new_request = VerifyRequest(
                methods=new_methods,
                required_for_confirmed=original_request.required_for_confirmed,
                required_for_review=original_request.required_for_review
            )
            new_requests.append((new_request, combined_reference_dict))

        return new_requests

    def _generate_variations(
        self,
        system_prompt_template: str,
        user_prompt_template: str,
        reference_data: List[Tuple[int, str, List[Any]]],
        other_attributes: Dict[str, Any] = None
    ) -> List[Tuple[VerificationMethod, Dict[str, str]]]:
        """
        Generates variations of prompts or methods by filling placeholders with reference data.
        Refactored to be used for both prompt and method variations.

        Args:
            system_prompt_template: The system prompt template.
            user_prompt_template: The user prompt template.
            reference_data: Data from referenced steps.
            other_attributes: Other attributes to include in the generated object (for methods).

        Returns:
            A list of tuples, each containing a generated object (prompt or method) and its reference data.
        """
        variations = []

        def generate_combinations(
            index: int,
            system_prompt: str,
            user_prompt: str,
            current_reference_dict: Dict[str, str]
        ) -> None:
            """
            Recursive helper function to generate prompt/method combinations.
            """
            if not self._has_placeholders(system_prompt) and not self._has_placeholders(user_prompt):
                if other_attributes:
                    # Create a VerificationMethod object
                    variations.append(
                        (
                            VerificationMethod(
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                **other_attributes
                            ),
                            current_reference_dict
                        )
                    )
                else:
                    # Create a prompt tuple
                    variations.append((system_prompt, user_prompt, current_reference_dict))
                return

            if index == len(reference_data):
                system_prompt, user_prompt, current_reference_dict = self._process_placeholders(system_prompt, user_prompt, self.global_references, current_reference_dict)
                if other_attributes:
                    variations.append(
                        (
                            VerificationMethod(
                                system_prompt=system_prompt,
                                user_prompt=user_prompt,
                                **other_attributes
                            ),
                            current_reference_dict
                        )
                    )
                else:
                    variations.append((system_prompt, user_prompt, current_reference_dict))
                return

            ref_index, step_type, step_results = reference_data[index]
            if step_type == "generate":
                for generated_result in step_results:
                    content = f"content_{ref_index}"
                    entry = {content: generated_result.content}
                    new_system_prompt, new_user_prompt, new_reference_dict = self._process_placeholders(system_prompt, user_prompt, entry, current_reference_dict.copy())
                    generate_combinations(index + 1, new_system_prompt, new_user_prompt, new_reference_dict)
            elif step_type == "parse":
                for parse_result in step_results:
                    for entry in parse_result.entries:
                        new_system_prompt, new_user_prompt, new_reference_dict = self._process_placeholders(system_prompt, user_prompt, entry, current_reference_dict.copy())
                        generate_combinations(index + 1, new_system_prompt, new_user_prompt, new_reference_dict)
            else:
                generate_combinations(index + 1, system_prompt, user_prompt, current_reference_dict)

        generate_combinations(
            index=0,
            system_prompt=system_prompt_template,
            user_prompt=user_prompt_template,
            current_reference_dict={}
        )
        return variations
    
    def _create_prompt_variations(
        self,
        request: GenerateTextRequest,
        reference_data: List[Tuple[int, str, List[Any]]]
    ) -> List[Tuple[str, str, Dict[str, str]]]:
        """
        Generates variations of prompts by filling placeholders with reference data.

        Args:
            request: The base GenerateTextRequest with system_prompt and user_prompt.
            reference_data: A list of tuples (ref_index, step_type, results) from referenced steps.

        Returns:
            A list of tuples (system_prompt, user_prompt, reference_dict).
        """
        variations = []

        def generate_combinations(
            index: int,
            system_prompt: str,
            user_prompt: str,
            current_reference_dict: Dict[str, str]
        ) -> None:
            """
            Recursive helper function to generate prompt combinations.
            """

            # Base Case 1
            if not self._has_placeholders(system_prompt) and not self._has_placeholders(user_prompt):
                variations.append((system_prompt, user_prompt, current_reference_dict))
                return

            # Base Case 2
            if index == len(reference_data):
                system_prompt, user_prompt, current_reference_dict = self._process_placeholders(system_prompt, user_prompt, self.global_references, current_reference_dict)
                variations.append((system_prompt, user_prompt, current_reference_dict))
                return

            # Recursive Case
            ref_index, step_type, step_results = reference_data[index]
            if step_type == "generate":
                generated_result: GeneratedResult
                for generated_result in step_results:
                    content = f"content_{ref_index}"
                    entry = {content: generated_result.content}
                    new_system_prompt, new_user_prompt, new_reference_dict = self._process_placeholders(system_prompt, user_prompt, entry, current_reference_dict.copy())
                    generate_combinations(index + 1, new_system_prompt, new_user_prompt, new_reference_dict)
       
            elif step_type == "parse":
                parse_result: ParseResult
                for parse_result in step_results:
                    entry = Dict[str, str]
                    for entry in parse_result.entries:
                        new_system_prompt, new_user_prompt, new_reference_dict = self._process_placeholders(system_prompt, user_prompt, entry, current_reference_dict.copy())
                        generate_combinations(index + 1, new_system_prompt, new_user_prompt, new_reference_dict)

            else: 
                generate_combinations(index + 1, new_system_prompt, new_user_prompt, new_reference_dict)
            
        generate_combinations(
            index=0,
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            current_reference_dict={}
        )
        return variations

    def _process_placeholders(self, system_prompt, user_prompt, references: Dict[str, str], reference_dict) -> Tuple[str, str, Dict[str, str]]:
        new_system_prompt = system_prompt
        new_user_prompt = user_prompt

        for reference_key, reference_value in references.items():
            new_system_prompt, replaced_flag_sys = self._replace_placeholders(new_system_prompt, {reference_key: reference_value})
            new_user_prompt, replaced_flag_usr = self._replace_placeholders(new_user_prompt, {reference_key: reference_value})

            if replaced_flag_sys or replaced_flag_usr:
                reference_dict[reference_key] = reference_value

        return new_system_prompt, new_user_prompt, reference_dict

    def _has_placeholders(self, text: str) -> Set[str]:
        """
        Checks if a text contains placeholders and returns a set of their names.

        Args:
            text: The text to check.

        Returns:
            A set of placeholders found (without braces).
        """
        return set(re.findall(r"{([^{}]+)}", text))

    def _replace_placeholders(self, text: str, placeholders: Dict[str, str]) -> Tuple[str, bool]:
        """
        Replaces placeholders in a text given a dictionary of placeholders.

        If a placeholder is not found in the dictionary, the text keeps the placeholder form {placeholder}.

        Args:
            text: The text in which to search and replace placeholders.
            placeholders: A key-value dictionary of placeholders and their replacements.

        Returns:
            A tuple: (replaced_text, was_modified).
        """
        placeholder_dict = PlaceholderDict(placeholders)
        modified_text = text.format_map(placeholder_dict)
        was_replaced = modified_text != text
        return modified_text, was_replaced

    def _get_reference_data(
        self,
        reference_step_numbers: List[int],
        current_step_number: int
    ) -> List[Tuple[int, str, List[Any]]]:
        """
        Retrieves the information from the referenced steps.

        Args:
            reference_step_numbers: A list of indices of steps being referenced.
            current_step_number: The index of the current step.

        Returns:
            A list of tuples (step_type, results) for each valid reference.
            Returns an empty list if any reference is invalid.
        """
        reference_data = []
        for ref_index in reference_step_numbers:
            if 0 <= ref_index < current_step_number and ref_index < len(self.results) and self.results[ref_index]:
                step_type, results = self.results[ref_index]
                reference_data.append((ref_index, step_type, results))
            else:
                logger.warning(f"Reference {ref_index} not found or invalid for step {current_step_number}. Returning empty result.")
                return []
        return reference_data