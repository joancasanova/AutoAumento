# app/main.py

import argparse
import json
import logging
from typing import Dict, Any, List

# Configurar el logging aquí (por simplicidad, lo hacemos en main.py)
logging.basicConfig(
    level=logging.INFO,  # Ajustar a DEBUG para mayor granularidad
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
    Carga un archivo JSON y devuelve un diccionario.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(data: Dict[str, Any], file_path: str):
    """
    Guarda un diccionario como JSON en un archivo.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_parser() -> argparse.ArgumentParser:
    """
    Crea un analizador de argumentos para la herramienta CLI, definiendo subcomandos para:
     - generate
     - parse
     - verify
     - pipeline
     - benchmark
    """
    parser = argparse.ArgumentParser(description="Pipeline de Procesamiento de Texto")

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # (1) Generate
    gen_parser = subparsers.add_parser("generate", help="Generar texto")
    gen_parser.add_argument(
        "--gen-model-name",
        default="Qwen/Qwen2.5-1.5B-Instruct",
        help="Nombre del modelo de lenguaje a usar"
    )
    gen_parser.add_argument("--system-prompt", required=True, help="Prompt del sistema")
    gen_parser.add_argument("--user-prompt", required=True, help="Prompt del usuario")
    gen_parser.add_argument(
        "--num-sequences", type=int, default=1, help="Número de secuencias a generar"
    )
    gen_parser.add_argument(
        "--max-tokens", type=int, default=50, help="Máximo de tokens a generar"
    )
    gen_parser.add_argument(
        "--temperature", type=float, default=1.0, help="Temperatura de generación"
    )
    gen_parser.add_argument(
        "--reference-data", type=str,
        help="Archivo JSON con datos de referencia para sustitución de placeholders"
    )

    # (2) Parse
    parse_parser = subparsers.add_parser("parse", help="Analizar texto")
    parse_parser.add_argument("--text", required=True, help="Texto a analizar")
    parse_parser.add_argument("--rules", required=True, help="Archivo JSON con reglas de análisis")
    parse_parser.add_argument(
        "--output-filter", type=str, default="all",
        choices=["all", "successful", "first", "first_n"],
        help="Filtrar resultados por criterio"
    )
    parse_parser.add_argument(
        "--output-limit", type=int, help="Número de entradas a devolver con el filtro first_n"
    )

    # (3) Verify
    verify_parser = subparsers.add_parser("verify", help="Verificar texto")
    verify_parser.add_argument(
        "--verify-model-name",
        default="Qwen/Qwen2.5-3B-Instruct",
        help="Nombre del modelo de lenguaje a usar"
    )
    verify_parser.add_argument(
        "--methods", required=True, help="Archivo JSON con métodos de verificación"
    )
    verify_parser.add_argument(
        "--required-confirmed", type=int, required=True, help="Confirmaciones requeridas"
    )
    verify_parser.add_argument(
        "--required-review", type=int, required=True, help="Revisiones requeridas"
    )
    verify_parser.add_argument(
        "--reference-data", type=str, help="Archivo JSON con datos de referencia para sustitución de placeholders"
    )

    # (4) Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Ejecutar pipeline")
    pipeline_parser.add_argument("--config", required=True, help="Archivo JSON con la configuración del pipeline")
    pipeline_parser.add_argument("--reference-data", type=str, help="Archivo JSON con datos de referencia globales para placeholders")

    # (5) Benchmark command (placeholder)
    benchmark_parser = subparsers.add_parser("benchmark", help="Ejecutar benchmark")
    benchmark_parser.add_argument("--config", required=True, help="Archivo JSON con la configuración del benchmark")
    benchmark_parser.add_argument("--entries", required=True, help="Archivo JSON con las entradas del benchmark")

    return parser

def parse_rules_from_json(file_path: str) -> List[ParseRule]:
    """
    Carga reglas de análisis desde un archivo JSON y las convierte en objetos ParseRule.
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
    Carga métodos de verificación desde un archivo JSON y los convierte en objetos VerificationMethod.
    """
    try:
        methods_data = load_json_file(file_path)
        if not isinstance(methods_data, list):
            raise ValueError("El archivo de métodos debe contener una lista de métodos de verificación")

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
                raise ValueError(f"Falta campo requerido en el método de verificación: {e}")
            except ValueError as e:
                raise ValueError(f"Datos inválidos en el método de verificación: {e}")
    except Exception as e:
        raise ValueError(f"Error al analizar los métodos de verificación: {e}")
    return methods

def format_verification_result(verify_response: VerifyResponse) -> Dict[str, Any]:
    """
    Convierte un objeto VerifyResponse en un diccionario estructurado para la salida JSON.
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
        logger.info(f"Ejecutando comando: {args.command}")
        result = None

        # Inicializar modelos LLM una vez para reutilizar
        llm = InstructModel(model_name="Qwen/Qwen2.5-1.5B-Instruct")

        if args.command == "generate":
            reference_data = load_json_file(args.reference_data) if args.reference_data else None
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
            reference_data = load_json_file(args.reference_data) if args.reference_data else None
            methods = parse_verification_methods_from_json(args.methods)
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
            pipeline_config = load_json_file(args.config)
            pipeline_steps = [PipelineStep(name=step["name"], type=step["type"]) for step in pipeline_config["steps"]]
            pipeline_params = pipeline_config["parameters"]

            global_ref_data = load_json_file(args.reference_data) if args.reference_data else None

            pipeline_service = PipelineService(llm=llm)
            pipeline_use_case = PipelineUseCase(pipeline_service)
            pipeline_request = PipelineRequest(
                steps=pipeline_steps,
                parameters=pipeline_params,
                global_reference_data=global_ref_data
            )
            pipeline_response = pipeline_use_case.execute(pipeline_request)

            print(json.dumps(pipeline_response.step_results, indent=2, ensure_ascii=False))

        elif args.command == "benchmark":
            logger.warning("Comando benchmark no implementado todavía.")

    except Exception as e:
        logger.exception("Ocurrió un error al ejecutar el comando.")
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()