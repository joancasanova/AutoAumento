# app/main.py

import argparse
import json
import logging
from typing import Dict, Any, List

# Configure the logging here (for simplicity, we do it in main.py)
logging.basicConfig(
    level=logging.INFO,  # Adjust level to DEBUG for more granularity
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

from infrastructure.external.llm.instruct_model import InstructModel
from application.use_cases.generate_text_use_case import (
    GenerateTextUseCase,
    GenerateTextRequest,
)
from application.use_cases.parse_generated_output_use_case import (
    ParseGeneratedOutputUseCase,
    ParseRequest,
)
from application.use_cases.verify_use_case import (
    VerifyUseCase,
    VerifyRequest,
)
from domain.model.entities.parsing import ParseMode, ParseRule
from domain.model.entities.verification import (
    VerificationMethod,
    VerificationMode,
    VerifyResponse
)
from domain.services.parse_service import ParseService
from domain.services.verifier_service import VerifierService
from domain.model.entities.pipeline import (
    PipelineStep,
    PipelineRequest
)
from application.use_cases.pipeline_use_case import PipelineUseCase
from domain.services.pipeline_service import PipelineService

logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Loads a JSON file and returns the parsed dictionary.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(data: Dict[str, Any], file_path: str):
    """
    Saves a dictionary as JSON to the specified file.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_parser() -> argparse.ArgumentParser:
    """
    Creates an argument parser for the CLI tool, defining subcommands for:
     - generate
     - parse
     - verify
     - pipeline
     - benchmark
    """
    parser = argparse.ArgumentParser(description="Text Processing Pipeline")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # (1) Generate
    gen_parser = subparsers.add_parser("generate", help="Generate text")
    gen_parser.add_argument(
        "--gen-model-name",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Name of the language model to use"
    )
    gen_parser.add_argument("--system-prompt", required=True, help="System prompt")
    gen_parser.add_argument("--user-prompt", required=True, help="User prompt")
    gen_parser.add_argument(
        "--num-sequences", type=int, default=1, help="Number of sequences to generate"
    )
    gen_parser.add_argument(
        "--max-tokens", type=int, default=50, help="Maximum tokens to generate"
    )
    gen_parser.add_argument(
        "--temperature", type=float, default=1.0, help="Generation temperature"
    )
    gen_parser.add_argument(
        "--reference-data", type=str,
        help="JSON file containing dictionary with reference data for placeholder substitution"
    )

    # (2) Parse
    parse_parser = subparsers.add_parser("parse", help="Parse text")
    parse_parser.add_argument("--text", required=True, help="Text to parse")
    parse_parser.add_argument("--rules", required=True, help="JSON file containing parse rules")
    parse_parser.add_argument(
        "--output-filter", type=str, default="all",
        choices=["all", "successful", "first", "first_n"],
        help="Filter entries by specified criteria"
    )
    parse_parser.add_argument(
        "--output-limit", type=int, help="Number of entries to return when output filter is first_n"
    )

    # (3) Verify
    verify_parser = subparsers.add_parser("verify", help="Verify")
    verify_parser.add_argument(
        "--verify-model-name",
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Name of the language model to use"
    )
    verify_parser.add_argument(
        "--methods", required=True, help="JSON file containing verification methods"
    )
    verify_parser.add_argument(
        "--required-confirmed", type=int, required=True, help="Required confirmations"
    )
    verify_parser.add_argument(
        "--required-review", type=int, required=True, help="Required reviews"
    )
    verify_parser.add_argument(
        "--reference-data", type=str, help="JSON file containing dictionary with reference data for placeholder substitution"
    )

    # (4) Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Execute pipeline")
    pipeline_parser.add_argument("--config", required=True, help="JSON file containing pipeline configuration")
    pipeline_parser.add_argument("--reference-data", type=str, help="JSON file containing global reference data for placeholders")

    # (5) Benchmark command (placeholder)
    benchmark_parser = subparsers.add_parser("benchmark", help="Run benchmark")
    benchmark_parser.add_argument("--config", required=True, help="JSON file containing benchmark configuration")
    benchmark_parser.add_argument("--entries", required=True, help="JSON file containing benchmark entries")

    return parser


def parse_rules_from_json(file_path: str) -> List[ParseRule]:
    """
    Helper function to load parse rules from a JSON file and convert them into ParseRule objects.
    """
    rules_data = load_json_file(file_path)
    rules = []
    for rule_data in rules_data:
        mode = ParseMode[rule_data.pop("mode").upper()]
        rule = ParseRule(mode=mode, **rule_data)
        rules.append(rule)
    return rules


def parse_verification_methods_from_json(file_path: str) -> List[VerificationMethod]:
    """
    Helper function to load verification methods from a JSON file and convert 
    them into a list of VerificationMethod objects.
    """
    try:
        methods_data = load_json_file(file_path)
        if not isinstance(methods_data, list):
            raise ValueError("Methods file must contain a list of verification methods")
        
        methods = []
        for method_data in methods_data:
            try:
                mode = VerificationMode[method_data.pop("mode").upper()]
                method = VerificationMethod(
                    mode=mode,
                    name=method_data["name"],
                    system_prompt=method_data["system_prompt"],
                    user_prompt=method_data["user_prompt"],
                    valid_responses=method_data["valid_responses"],
                    num_sequences=method_data.get("num_sequences", 3),
                    required_matches=method_data.get("required_matches")
                )
                methods.append(method)
            except KeyError as e:
                raise ValueError(f"Missing required field in verification method: {e}")
            except ValueError as e:
                raise ValueError(f"Invalid verification method data: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse verification methods: {e}")
    return methods


def format_verification_result(verify_response: VerifyResponse) -> Dict[str, Any]:
    """
    Converts a VerifyResponse object into a structured dictionary suitable for JSON output.
    """
    summary = verify_response.verification_summary
    results_formatted = []

    for r in summary.results:
        results_formatted.append({
            "method_name": r.method.name,
            "mode": r.method.mode.value,
            "passed": r.passed,
            "score": r.score,
            "timestamp": r.timestamp.isoformat(),
            "details": r.details
        })

    formatted_output = {
        "final_status": summary.final_status,
        "success_rate": verify_response.success_rate,
        "execution_time": verify_response.execution_time,
        "results": results_formatted
    }

    return formatted_output


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        logger.info(f"Running command: {args.command}")
        result = None

        # Initialize LLM models once to reuse across steps
        # Default models can be overridden per step
        llm = InstructModel(model_name="Qwen/Qwen2.5-1.5B-Instruct")

        if args.command == "generate":
            # Merge reference data if provided
            reference_data = None
            if args.reference_data:
                reference_data = load_json_file(args.reference_data)

            # Utilize the pre-instantiated LLM model for generation
            generate_use_case = GenerateTextUseCase(llm)
            
            request = GenerateTextRequest(
                system_prompt=args.system_prompt,
                user_prompt=args.user_prompt,
                num_sequences=args.num_sequences,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                reference_data=reference_data
            )
            response = generate_use_case.execute(request)
            # Serialize the response
            response_dict = {
                "generated_texts": [gen.content for gen in response.generated_texts],
                "total_tokens": response.total_tokens,
                "generation_time": response.generation_time,
                "model_name": response.model_name
            }
            print(json.dumps(response_dict, indent=2))

        elif args.command == "parse":
            parse_service = ParseService()
            parse_use_case = ParseGeneratedOutputUseCase(parse_service)

            rules = parse_rules_from_json(args.rules)
            request = ParseRequest(
                text=args.text,
                rules=rules,
                output_filter=args.output_filter,
                output_limit=args.output_limit
            )
            response = parse_use_case.execute(request)
            print(json.dumps(response.parse_result.to_list_of_dicts(), indent=2))

        elif args.command == "verify":
            # Merge reference data if provided
            reference_data = None
            if args.reference_data:
                reference_data = load_json_file(args.reference_data)

            methods = parse_verification_methods_from_json(args.methods)

            # Utilize the pre-instantiated LLM model for verification
            verifier_service = VerifierService(llm)
            verify_use_case = VerifyUseCase(verifier_service)

            request = VerifyRequest(
                methods=methods,
                required_for_confirmed=args.required_confirmed,
                required_for_review=args.required_review,
                reference_data=reference_data
            )
            response = verify_use_case.execute(request)

            formatted_result = format_verification_result(response)
            print(json.dumps(formatted_result, indent=2))

        elif args.command == "pipeline":
            # Load pipeline_config.json
            pipeline_config = load_json_file(args.config)
            steps_data = pipeline_config["steps"]
            pipeline_steps = []
            for step_data in steps_data:
                step_type = step_data["type"]
                params = step_data["params"]
                pipeline_steps.append(PipelineStep(step_type=step_type, params=params))

            # Load global reference data if provided
            global_ref_data = None
            if args.reference_data:
                global_ref_data = load_json_file(args.reference_data)

            # Initialize PipelineService with pre-instantiated LLM models
            pipeline_service = PipelineService(llm=llm)
            pipeline_use_case = PipelineUseCase(pipeline_service)

            pipeline_request = PipelineRequest(
                steps=pipeline_steps,
                global_reference_data=global_ref_data
            )
            pipeline_response = pipeline_use_case.execute(pipeline_request)

            # Serialize the pipeline results
            final_output = []
            for step_result in pipeline_response.step_results:
                final_output.append({
                    "step_type": step_result.step_type,
                    "input_data": step_result.input_data,
                    "output_data": step_result.output_data
                })

            print(json.dumps(final_output, indent=2))

        # Additional commands (benchmark) placeholders
        elif args.command == "benchmark":
            logger.warning("Benchmark command not yet implemented.")

    except Exception as e:
        logger.exception("An error occurred while executing the command.")
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
