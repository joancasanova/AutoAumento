import argparse
import json
import logging
from typing import Dict, Any, List, Callable

from domain.model.entities.benchmark import BenchmarkConfig, BenchmarkEntry, BenchmarkMetrics
from infrastructure.file_repository import FileRepository

# Basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Imports of use cases and models
from application.use_cases.benchmark_use_case import BenchmarkUseCase
from application.use_cases.generate_text_use_case import (
    GenerateTextUseCase,
    GenerateTextRequest,
)
from application.use_cases.parse_use_case import (
    ParseUseCase,
    ParseRequest,
)
from application.use_cases.verify_use_case import (
    VerifyUseCase,
    VerifyRequest,
)
from domain.model.entities.parsing import ParseMode, ParseRule
from domain.model.entities.verification import (
    VerificationMethod,
    VerificationMode
)
from domain.model.entities.pipeline import (
    PipelineResponse,
    PipelineStep,
    PipelineRequest
)
from application.use_cases.pipeline_use_case import PipelineUseCase

# Type for command handlers
CommandHandler = Callable[[argparse.Namespace], None]

class CommandProcessor:
    """Base class for command processing with common utilities"""
    
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        """Loads a JSON file and returns a dictionary."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def parse_rules(rules_data: List[Dict]) -> List[ParseRule]:
        """Converts JSON data into ParseRule objects."""
        rules = []
        for rule_data in rules_data:
            mode = ParseMode[rule_data.pop("mode").upper()]
            rules.append(ParseRule(mode=mode, **rule_data))
        return rules

    @staticmethod
    def parse_verification_methods(methods_data: List[Dict]) -> List[VerificationMethod]:
        """Converts JSON data into VerificationMethod objects."""
        methods = []
        for method_data in methods_data:
            mode = VerificationMode[method_data.pop("mode").upper()]
            methods.append(VerificationMethod(
                mode=mode,
                name=method_data["name"],
                system_prompt=method_data["system_prompt"],
                user_prompt=method_data["user_prompt"],
                valid_responses=method_data["valid_responses"],
                num_sequences=method_data.get("num_sequences", 3),
                required_matches=method_data.get("required_matches")
            ))
        return methods

    @staticmethod
    def parse_pipeline_steps(config: Dict) -> List[PipelineStep]:
        """Parses pipeline configuration into a list of steps."""
        steps = []
        for step_data in config["steps"]:
            step_type = step_data["type"]
            
            # Create parameters based on step type
            if step_type == "generate":
                parameters = GenerateTextRequest(**step_data["parameters"])
            elif step_type == "parse":
                parameters = ParseRequest(
                    text=step_data["parameters"].get("text"),
                    rules=CommandProcessor.parse_rules(step_data["parameters"]["rules"]),
                    output_filter=step_data["parameters"].get("output_filter", "all"),
                    output_limit=step_data["parameters"].get("output_limit")
                )
            elif step_type == "verify":
                parameters = VerifyRequest(
                    methods=CommandProcessor.parse_verification_methods(
                        step_data["parameters"]["methods"]
                    ),
                    required_for_confirmed=step_data["parameters"]["required_for_confirmed"],
                    required_for_review=step_data["parameters"]["required_for_review"]
                )
            else:
                raise ValueError(f"Invalid step type: {step_type}")

            steps.append(PipelineStep(
                type=step_type,
                parameters=parameters,
                uses_reference=step_data.get("uses_reference", False),
                reference_step_numbers=step_data.get("reference_step_numbers", [])
            ))
        return steps

class OutputFormatter:
    """Class for formatting different types of outputs"""
    
    @staticmethod
    def print_pipeline_results(response: PipelineResponse):
        """Prints pipeline results in a readable format."""
        for i, step_result in enumerate(response.step_results):
            print(f"\n--- Step {i}: {step_result['step_type']} ---")
            OutputFormatter._print_step_data(step_result['step_data'])

    @staticmethod
    def _print_step_data(step_data: List[Any]):
        """Handles printing of different data types in steps"""
        for i, item in enumerate(step_data, 1):
            if isinstance(item, dict):
                OutputFormatter._print_dict_item(item, i)
            else:
                print(f"  Result {i}: {item}")

    @staticmethod
    def _print_dict_item(item: Dict, index: int):
        """Handles printing of specific dictionary items"""
        if 'content' in item:
            OutputFormatter._print_generation_result(item, index)
        elif 'final_status' in item:
            OutputFormatter._print_verification_result(item, index)
        elif 'entries' in item:
            OutputFormatter._print_parsing_result(item, index)

    @staticmethod
    def _print_generation_result(item: Dict, index: int):
        """Prints generation results"""
        print(f"\n  Result {index}:")
        print(f"    - Content: {item['content']}")
        if 'metadata' in item:
            print("    - Metadata:")
            print(f"      -- System prompt: {item['metadata']['system_prompt']}")
            print(f"      -- User prompt: {item['metadata']['user_prompt']}")
        if 'reference_data' in item and item['reference_data']:
            print("    - Reference data:")
            for k, v in item['reference_data'].items():
                print(f"      -- {k}: {v}")

    @staticmethod
    def _print_verification_result(item: Dict, index: int):
        """Prints verification results"""
        print(f"  Verification result {index}:")
        print(f"    Final status: {item['final_status']}")
        print(f"    Success rate: {item['success_rate']:.2f}")
        print(f"    Reference data: {item['reference_data']}")
        print("    Results:")
        for result in item['results']:
            print(f"      Method: {result['method_name']}")
            print(f"        Mode: {result['mode']}")
            print(f"        Passed: {result['passed']}")
            print(f"        Score: {result['score']:.2f}")
            print(f"        Timestamp: {result['timestamp']}")
            print(f"        Details: {result['details']}")

    @staticmethod
    def _print_parsing_result(item: Dict, index: int):
        """Prints parsing results"""
        print(f"  Parsing result {index}:")
        for j, entry in enumerate(item['entries'], 1):
            print(f"    Entry {j}:")
            for key, value in entry.items():
                print(f"      {key}: {value}")

    @staticmethod
    def print_benchmark_results(metrics: BenchmarkMetrics):
        print("\n=== Benchmark Results ===")
        print(f"• Accuracy: {metrics.accuracy:.2%}")
        print(f"• Precision: {metrics.precision:.2%}")
        print(f"• Recall: {metrics.recall:.2%}")
        print(f"• F1-Score: {metrics.f1_score:.2%}")
        print("\nConfusion Matrix:")
        print(f"True Positives: {metrics.confusion_matrix['true_positive']}")
        print(f"False Positives: {metrics.confusion_matrix['false_positive']}")
        print(f"True Negatives: {metrics.confusion_matrix['true_negative']}")
        print(f"False Negatives: {metrics.confusion_matrix['false_negative']}")
        print(f"Total cases evaluated: {len(metrics.misclassified) + metrics.confusion_matrix['true_positive'] + metrics.confusion_matrix['false_positive'] + metrics.confusion_matrix['true_negative']}")
        print(f"\nMisclassified cases saved in: misclassified_*.json")

def setup_arg_parser() -> argparse.ArgumentParser:
    """Sets up the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Text Processing Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Command registration
    commands = {
        "generate": setup_generate_parser,
        "parse": setup_parse_parser,
        "verify": setup_verify_parser,
        "pipeline": setup_pipeline_parser,
        "benchmark": setup_benchmark_parser
    }

    for cmd, setup_fn in commands.items():
        subparser = subparsers.add_parser(cmd, help=f"{cmd} command")
        setup_fn(subparser)

    return parser

def setup_generate_parser(parser: argparse.ArgumentParser):
    """Sets up the parser for the generate command"""
    parser.add_argument(
        "--gen-model-name",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Name of the language model to use"
    )
    parser.add_argument("--system-prompt", required=True)
    parser.add_argument("--user-prompt", required=True)
    parser.add_argument("--num-sequences", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=50)
    parser.add_argument("--temperature", type=float, default=1.0)

def setup_parse_parser(parser: argparse.ArgumentParser):
    """Sets up the parser for the parse command"""
    parser.add_argument("--text", required=True)
    parser.add_argument("--rules",
                      default="config/parse/parse_rules.json",
                      help="Path to the parsing rules file")
    parser.add_argument(
        "--output-filter", 
        choices=["all", "successful", "first", "first_n"], 
        default="all"
    )
    parser.add_argument("--output-limit", type=int)

def setup_verify_parser(parser: argparse.ArgumentParser):
    """Sets up the parser for the verify command"""
    parser.add_argument(
        "--verify-model-name",
        default="Qwen/Qwen2.5-1.5B-Instruct"
    )
    parser.add_argument("--methods",
                      default="config/parse/verify_methods.json",
                      help="Path to the verification methods file")
    parser.add_argument("--required-confirmed", type=int, required=True)
    parser.add_argument("--required-review", type=int, required=True)

def setup_pipeline_parser(parser: argparse.ArgumentParser):
    """Sets up the parser for the pipeline command"""
    parser.add_argument("--config",
                      default="config/pipeline/pipeline_config.json",
                      help="Path to the pipeline configuration file")
    parser.add_argument(
        "--pipeline-generation-model-name", 
        default="Qwen/Qwen2.5-1.5B-Instruct"
    )    
    parser.add_argument(
        "--pipeline-verify-model-name", 
        default="Qwen/Qwen2.5-1.5B-Instruct"
    )

def setup_benchmark_parser(parser: argparse.ArgumentParser):
    """Sets up the parser for the benchmark command"""
    parser.add_argument("--config", 
                      default="config/benchmark/benchmark_config.json",
                      help="Path to the benchmark configuration file")
    parser.add_argument("--entries",
                      default="config/benchmark/benchmark_entries.json",
                      help="Path to the benchmark entries file")

def handle_generate(args: argparse.Namespace):
    """Handler for the generate command"""
    use_case = GenerateTextUseCase(args.gen_model_name)
    response = use_case.execute(GenerateTextRequest(
        system_prompt=args.system_prompt,
        user_prompt=args.user_prompt,
        num_sequences=args.num_sequences,
        max_tokens=args.max_tokens,
        temperature=args.temperature
    ))
    
    result = {
        "generated_texts": [gen.content for gen in response.generated_texts],
        "total_tokens": response.total_tokens,
        "generation_time": response.generation_time,
        "model_name": response.model_name
    }
    print(json.dumps(result, indent=2))

def handle_parse(args: argparse.Namespace):
    """Handler for the parse command"""
    rules = CommandProcessor.parse_rules(
        CommandProcessor.load_json_file(args.rules)
    )
    
    response = ParseUseCase().execute(ParseRequest(
        text=args.text,
        rules=rules,
        output_filter=args.output_filter,
        output_limit=args.output_limit
    ))
    
    print(json.dumps(response.parse_result.to_list_of_dicts(), indent=2))

def handle_verify(args: argparse.Namespace):
    """Handler for the verify command"""
    methods = CommandProcessor.parse_verification_methods(
        CommandProcessor.load_json_file(args.methods)
    )
    
    response = VerifyUseCase(args.verify_model_name).execute(VerifyRequest(
        methods=methods,
        required_for_confirmed=args.required_confirmed,
        required_for_review=args.required_review
    ))
    
    print(json.dumps({
        "final_status": response.verification_summary.final_status,
        "success_rate": response.success_rate,
        "execution_time": response.execution_time,
        "results": [{
            "method_name": r.method.name,
            "mode": r.method.mode.value,
            "passed": r.passed,
            "score": r.score,
            "timestamp": r.timestamp.isoformat(),
            "details": r.details
        } for r in response.verification_summary.results]
    }, indent=2))

def handle_pipeline(args: argparse.Namespace):
    """Handler for the pipeline command"""
    config = CommandProcessor.load_json_file(args.config)
    pipeline_steps = CommandProcessor.parse_pipeline_steps(config)
    
    reference_data_path = "config/pipeline/pipeline_reference_data.json"
    try:
        with open(reference_data_path, 'r') as f:
            reference_entries = json.load(f)
    except Exception as e:
        logger.error(f"Error loading reference data: {str(e)}")
        raise
    
    response = PipelineUseCase(
        args.pipeline_generation_model_name, 
        args.pipeline_verify_model_name
    ).execute_with_references(
        PipelineRequest(
            steps=pipeline_steps,
            global_references=config.get("global_references", {})
        ),
        reference_entries=reference_entries  
    )

    FileRepository.append(
        data=response.step_results,
        output_dir="out/pipeline/results",
        filename="pipeline_results.json"
    )
    
    for result_type in ['confirmed', 'to_verify']:
        entries = response.verification_references.get(result_type, [])
        if entries:
            output_dir = f"out/pipeline/verification/{result_type}"
            filename = f"{result_type}.json"
            
            for entry in entries:
                FileRepository.append(
                    data=entry,
                    output_dir=output_dir,
                    filename=filename
                )

    OutputFormatter.print_pipeline_results(response)

def handle_benchmark(args: argparse.Namespace):
    """Handler for the benchmark command"""
    config_data = CommandProcessor.load_json_file(args.config)
    entries_data = CommandProcessor.load_json_file(args.entries)
    
    # Convert to entities
    benchmark_config = BenchmarkConfig(
        model_name=config_data.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct"),
        pipeline_steps=CommandProcessor.parse_pipeline_steps(config_data),
        label_key=config_data["label_key"],
        label_value=config_data["label_value"]
    )
    
    benchmark_entries = [
        BenchmarkEntry(
            input_data={k: v for k, v in entry.items() if k != benchmark_config.label_key},
            expected_label=entry.get(benchmark_config.label_key, "")
        )
        for entry in entries_data
    ]
    
    use_case = BenchmarkUseCase(benchmark_config.model_name)
    metrics = use_case.run_benchmark(benchmark_config, benchmark_entries)  # Capture metrics
    
    # Save results
    FileRepository.save(
        metrics.to_dict(),
        output_dir="out/benchmark/results",
        filename_prefix="benchmark_results"
    )
    
    if metrics.misclassified:
        FileRepository.save(
            [result.to_dict() for result in metrics.misclassified],
            output_dir="out/benchmark/misclassified",
            filename_prefix="misclassified"
        )
    
    OutputFormatter.print_benchmark_results(metrics)
    
def main():
    """Main function of the program"""
    command_handlers: Dict[str, CommandHandler] = {
        "generate": handle_generate,
        "parse": handle_parse,
        "verify": handle_verify,
        "pipeline": handle_pipeline,
        "benchmark": handle_benchmark
    }

    parser = setup_arg_parser()
    args = parser.parse_args()

    try:
        logger.info("Starting execution of command: %s", args.command)
        command_handlers[args.command](args)
    except Exception as e:
        logger.exception("Error during command execution")
        print(f"\nERROR: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()