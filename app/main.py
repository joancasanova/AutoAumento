import argparse
import json
import logging
from typing import Dict, Any, List, Callable

from app.domain.model.entities.benchmark import BenchmarkConfig, BenchmarkEntry

# Configuración básica de logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Importaciones de casos de uso y modelos
from app.application.use_cases.benchmark_use_case import BenchmarkUseCase
from application.use_cases.generate_text_use_case import (
    GenerateTextUseCase,
    GenerateTextRequest,
)
from app.application.use_cases.parse_use_case import (
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
    VerificationMode,
    VerifyResponse
)
from domain.model.entities.pipeline import (
    PipelineResponse,
    PipelineStep,
    PipelineRequest
)
from application.use_cases.pipeline_use_case import PipelineUseCase

# Tipo para manejadores de comandos
CommandHandler = Callable[[argparse.Namespace], None]

class CommandProcessor:
    """Clase base para procesamiento de comandos con utilidades comunes"""
    
    @staticmethod
    def load_json_file(file_path: str) -> Dict[str, Any]:
        """Carga un archivo JSON y devuelve un diccionario."""
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def parse_rules(rules_data: List[Dict]) -> List[ParseRule]:
        """Convierte datos JSON en objetos ParseRule."""
        rules = []
        for rule_data in rules_data:
            mode = ParseMode[rule_data.pop("mode").upper()]
            rules.append(ParseRule(mode=mode, **rule_data))
        return rules

    @staticmethod
    def parse_verification_methods(methods_data: List[Dict]) -> List[VerificationMethod]:
        """Convierte datos JSON en objetos VerificationMethod."""
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
        """Parsea la configuración del pipeline en una lista de pasos."""
        steps = []
        for step_data in config["steps"]:
            step_type = step_data["type"]
            
            # Crear parámetros según el tipo de paso
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
                raise ValueError(f"Tipo de paso no válido: {step_type}")

            steps.append(PipelineStep(
                type=step_type,
                parameters=parameters,
                uses_reference=step_data.get("uses_reference", False),
                reference_step_numbers=step_data.get("reference_step_numbers", [])
            ))
        return steps

class OutputFormatter:
    """Clase para formatear diferentes tipos de salidas"""
    
    @staticmethod
    def print_pipeline_results(response: PipelineResponse):
        """Imprime resultados del pipeline de forma legible."""
        for i, step_result in enumerate(response.step_results):
            print(f"\n--- Paso {i}: {step_result['step_type']} ---")
            OutputFormatter._print_step_data(step_result['step_data'])

    @staticmethod
    def _print_step_data(step_data: List[Any]):
        """Maneja la impresión de diferentes tipos de datos en los pasos"""
        for i, item in enumerate(step_data, 1):
            if isinstance(item, dict):
                OutputFormatter._print_dict_item(item, i)
            else:
                print(f"  Resultado {i}: {item}")

    @staticmethod
    def _print_dict_item(item: Dict, index: int):
        """Maneja la impresión de elementos de diccionario específicos"""
        if 'content' in item:
            OutputFormatter._print_generation_result(item, index)
        elif 'final_status' in item:
            OutputFormatter._print_verification_result(item, index)
        elif 'entries' in item:
            OutputFormatter._print_parsing_result(item, index)

    @staticmethod
    def _print_generation_result(item: Dict, index: int):
        """Imprime resultados de generación"""
        print(f"\n  Resultado {index}:")
        print(f"    - Contenido: {item['content']}")
        if 'metadata' in item:
            print("    - Metadatos:")
            print(f"      -- System prompt: {item['metadata']['system_prompt']}")
            print(f"      -- User prompt: {item['metadata']['user_prompt']}")
        if 'reference_data' in item and item['reference_data']:
            print("    - Datos de referencia:")
            for k, v in item['reference_data'].items():
                print(f"      -- {k}: {v}")

    @staticmethod
    def _print_verification_result(item: Dict, index: int):
        """Imprime resultados de verificación"""
        print(f"  Resultado de verificación {index}:")
        print(f"    Estado final: {item['final_status']}")
        print(f"    Tasa de éxito: {item['success_rate']:.2f}")
        print(f"    Tiempo de ejecución: {item['execution_time']:.2f} segundos")
        print("    Resultados:")
        for result in item['results']:
            print(f"      Método: {result['method_name']}")
            print(f"        Modo: {result['mode']}")
            print(f"        Pasó: {result['passed']}")
            print(f"        Puntuación: {result['score']:.2f}")
            print(f"        Fecha y hora: {result['timestamp']}")
            print(f"        Detalles: {result['details']}")

    @staticmethod
    def _print_parsing_result(item: Dict, index: int):
        """Imprime resultados de análisis"""
        print(f"  Resultado de análisis {index}:")
        for j, entry in enumerate(item['entries'], 1):
            print(f"    Entrada {j}:")
            for key, value in entry.items():
                print(f"      {key}: {value}")

def setup_arg_parser() -> argparse.ArgumentParser:
    """Configura el parser de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Pipeline de Procesamiento de Texto")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Registro de comandos
    commands = {
        "generate": setup_generate_parser,
        "parse": setup_parse_parser,
        "verify": setup_verify_parser,
        "pipeline": setup_pipeline_parser,
        "benchmark": setup_benchmark_parser
    }

    for cmd, setup_fn in commands.items():
        subparser = subparsers.add_parser(cmd, help=f"Comando {cmd}")
        setup_fn(subparser)

    return parser

def setup_generate_parser(parser: argparse.ArgumentParser):
    """Configura el parser para el comando generate"""
    parser.add_argument(
        "--gen-model-name",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Nombre del modelo de lenguaje a usar"
    )
    parser.add_argument("--system-prompt", required=True)
    parser.add_argument("--user-prompt", required=True)
    parser.add_argument("--num-sequences", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=50)
    parser.add_argument("--temperature", type=float, default=1.0)

def setup_parse_parser(parser: argparse.ArgumentParser):
    """Configura el parser para el comando parse"""
    parser.add_argument("--text", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument(
        "--output-filter", 
        choices=["all", "successful", "first", "first_n"], 
        default="all"
    )
    parser.add_argument("--output-limit", type=int)

def setup_verify_parser(parser: argparse.ArgumentParser):
    """Configura el parser para el comando verify"""
    parser.add_argument(
        "--verify-model-name",
        default="Qwen/Qwen2.5-1.5B-Instruct"
    )
    parser.add_argument("--methods", required=True)
    parser.add_argument("--required-confirmed", type=int, required=True)
    parser.add_argument("--required-review", type=int, required=True)

def setup_pipeline_parser(parser: argparse.ArgumentParser):
    """Configura el parser para el comando pipeline"""
    parser.add_argument("--config", required=True)
    parser.add_argument(
        "--pipeline-model-name", 
        default="Qwen/Qwen2.5-1.5B-Instruct"
    )

def setup_benchmark_parser(parser: argparse.ArgumentParser):
    """Configura el parser para el comando benchmark"""
    parser.add_argument("--config", required=True)
    parser.add_argument("--entries", required=True)

def handle_generate(args: argparse.Namespace):
    """Manejador para el comando generate"""
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
    """Manejador para el comando parse"""
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
    """Manejador para el comando verify"""
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
    """Manejador para el comando pipeline"""
    config = CommandProcessor.load_json_file(args.config)
    pipeline_steps = CommandProcessor.parse_pipeline_steps(config)
    
    response = PipelineUseCase(args.pipeline_model_name).execute(
        PipelineRequest(
            steps=pipeline_steps,
            global_references=config.get("global_references", {})
        )
    )
    
    OutputFormatter.print_pipeline_results(response)

def handle_benchmark(args: argparse.Namespace):
    config_data = CommandProcessor.load_json_file(args.config)
    entries_data = CommandProcessor.load_json_file(args.entries)
    
    # Convertir a entidades
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
    use_case.run_benchmark(benchmark_config, benchmark_entries)
    
def main():
    """Función principal del programa"""
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
        logger.info("Iniciando ejecución del comando: %s", args.command)
        command_handlers[args.command](args)
    except Exception as e:
        logger.exception("Error durante la ejecución del comando")
        print(f"\nERROR: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()