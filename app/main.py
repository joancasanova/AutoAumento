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

logger = logging.getLogger(__name__)

def print_pipeline_results(pipeline_response: PipelineResponse):
    """
    Imprime los resultados del pipeline de una manera más legible.
    """
    for i, step_result in enumerate(pipeline_response.step_results):
        print(f"--- Paso {i}: {step_result['step_type']} ---")
        for i, item in enumerate(step_result['step_data']):
            if isinstance(item, dict):
                if 'content' in item:
                    print(f"\n  Resultado {i+1}:")
                    print(f"    - Contenido: {item['content']}")
                    if 'metadata' in item:
                        print(f"    - Metadatos:")
                        print(f"      -- System prompt: {item['metadata']['system_prompt']}")
                        print(f"      -- User prompt: {item['metadata']['user_prompt']}")
                    if 'reference_data' in item and item['reference_data']:
                        print(f"    - Datos de referencia:")
                        for ref_key, ref_value in item['reference_data'].items():
                            print(f"      -- {ref_key}: {ref_value}")
                elif 'final_status' in item:
                    print(f"  Resultado de verificación {i+1}:")
                    print(f"    Estado final: {item['final_status']}")
                    print(f"    Tasa de éxito: {item['success_rate']:.2f}")
                    print(f"    Tiempo de ejecución: {item['execution_time']:.2f} segundos")
                    print(f"    Resultados:")
                    for result in item['results']:
                        print(f"      Método: {result['method_name']}")
                        print(f"        Modo: {result['mode']}")
                        print(f"        Pasó: {result['passed']}")
                        print(f"        Puntuación: {result['score']:.2f}")
                        print(f"        Fecha y hora: {result['timestamp']}")
                        print(f"        Detalles: {result['details']}")
                elif 'entries' in item:
                    print(f"  Resultado de análisis {i+1}:")
                    for j, entry in enumerate(item['entries']):
                        print(f"    Entrada {j+1}:")
                        for key, value in entry.items():
                            print(f"      {key}: {value}")

            else:
                print(f"  Resultado {i+1}: {item}")  # Para otros tipos de datos
            
        print()

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
        default="Qwen/Qwen2.5-1.5B-Instruct",
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

    # (4) Pipeline command
    pipeline_parser = subparsers.add_parser("pipeline", help="Ejecutar pipeline")
    pipeline_parser.add_argument("--config", required=True, help="Archivo JSON con la configuración del pipeline")
    pipeline_parser.add_argument("--pipeline-model-name", default="Qwen/Qwen2.5-1.5B-Instruct", help="Nombre del modelo de lenguaje a usar")

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

        if args.command == "generate":
            generate_use_case = GenerateTextUseCase(args.gen_model_name)
            request = GenerateTextRequest(
                system_prompt=args.system_prompt,
                user_prompt=args.user_prompt,
                num_sequences=args.num_sequences,
                max_tokens=args.max_tokens,
                temperature=args.temperature
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
            parse_use_case = ParseUseCase()
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
            methods = parse_verification_methods_from_json(args.methods)
            verify_use_case = VerifyUseCase(args.verify_model_name)
            request = VerifyRequest(
                methods=methods,
                required_for_confirmed=args.required_confirmed,
                required_for_review=args.required_review
            )
            response = verify_use_case.execute(request)
            formatted_result = format_verification_result(response)
            print(json.dumps(formatted_result, indent=2))

        elif args.command == "pipeline":
            pipeline_config = load_json_file(args.config)

            pipeline_steps = []
            for step_data in pipeline_config["steps"]:
                if step_data["type"] == "generate":
                    parameters = GenerateTextRequest(**step_data["parameters"])  # Crear GenerateTextRequest
                elif step_data["type"] == "parse":
                    parameters = ParseRequest(text=step_data["parameters"]["text"], rules=parse_rules_from_json(step_data["parameters"]["rules"]))
                elif step_data["type"] == "verify":
                    parameters = VerifyRequest(
                            methods=parse_verification_methods_from_json(step_data["parameters"]["methods"]),
                            required_for_confirmed=step_data["parameters"]["required_for_confirmed"],
                            required_for_review=step_data["parameters"]["required_for_review"]
                        )
                else:
                    raise ValueError(f"Unknown step type: {step_data['type']}")
                
                pipeline_steps.append(
                    PipelineStep(
                        type=step_data["type"],
                        parameters=parameters,  # Usar el objeto creado
                        uses_reference=step_data.get("uses_reference", False),
                        reference_step_numbers=step_data.get("reference_step_numbers", []),
                        uses_verification=step_data.get("uses_verification", False),
                        verification_step_number=step_data.get("verification_step_number", 0)
                    )
                )

            global_references = pipeline_config["global_references"] 

            
            pipeline_use_case = PipelineUseCase(args.pipeline_model_name)
            pipeline_request = PipelineRequest(
                steps=pipeline_steps,
                global_references=global_references
            )
            pipeline_response = pipeline_use_case.execute(pipeline_request)

            print_pipeline_results(pipeline_response)

        elif args.command == "benchmark":
            logger.warning("Comando benchmark no implementado todavía.")

    except Exception as e:
        logger.exception("Ocurrió un error al ejecutar el comando.")
        print(f"Ocurrió un error: {e}")

if __name__ == "__main__":
    main()