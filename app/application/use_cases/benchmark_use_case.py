from collections import defaultdict
from typing import Any, Dict, List
from app.application.use_cases.pipeline_use_case import PipelineUseCase
from app.domain.model.entities.generation import GenerateTextRequest
from app.domain.model.entities.parsing import ParseRequest
from app.domain.model.entities.pipeline import PipelineRequest, PipelineStep
from app.domain.model.entities.verification import VerifyRequest
from app.main import load_json_file, parse_rules_from_json, parse_verification_methods_from_json, save_json_file


class BenchmarkUseCase:
    """
    Clase que se encarga de ejecutar benchmarks para evaluar el rendimiento
    del pipeline en un conjunto de datos de prueba.
    """

    def __init__(self, model_name: str, config_path: str, entries_path: str):
        """
        Inicializa el evaluador de benchmarks.

        Args:
            model_name (str): Nombre del modelo a utilizar para la generación de texto.
            config_path (str): Ruta al archivo JSON con la configuración del pipeline.
            entries_path (str): Ruta al archivo JSON con los datos de prueba.
        """
        self.model_name = model_name
        self.pipeline_config = load_json_file(config_path)
        self.benchmark_entries = load_json_file(entries_path)

    def run_benchmark(self):
        """
        Ejecuta el benchmark y muestra los resultados.
        """

        results = []
        for entry in self.benchmark_entries:
            input_data = entry["input"]
            expected_output = entry["output"]
            label = entry["label"]

            # Ejecutar el pipeline con los datos de entrada
            pipeline_steps = self._create_pipeline_steps(input_data)
            pipeline_use_case = PipelineUseCase(self.model_name)
            pipeline_request = PipelineRequest(
                steps=pipeline_steps,
                global_references=input_data.get("global_references", {})
            )
            pipeline_response = pipeline_use_case.execute(pipeline_request)

            # Obtener el resultado de la verificación
            verify_step_result = None
            for step_result in pipeline_response.step_results:
                if step_result["step_type"] == "verify":
                    verify_step_result = step_result
                    break

            if verify_step_result:
                # Comparar el resultado con el valor esperado
                verification_summary = verify_step_result["step_data"][-1]
                predicted_label = "positive" if verification_summary["final_status"] == "confirmed" else "negative"

                results.append({
                    "input": input_data,
                    "expected_output": expected_output,
                    "predicted_label": predicted_label,
                    "actual_label": label
                })

        # Calcular métricas de evaluación
        self._calculate_metrics(results)

    def _create_pipeline_steps(self, input_data: Dict[str, Any]) -> List[PipelineStep]:
        """
        Crea los pasos del pipeline a partir de la configuración y los datos de entrada.

        Args:
            input_data (Dict[str, Any]): Datos de entrada para el pipeline.

        Returns:
            List[PipelineStep]: Lista de pasos del pipeline.
        """
        pipeline_steps = []
        for step_data in self.pipeline_config["steps"]:
            if step_data["type"] == "generate":
                # Reemplazar placeholders en los prompts
                system_prompt = step_data["parameters"]["system_prompt"]
                user_prompt = step_data["parameters"]["user_prompt"]
                for key, value in input_data.items():
                    system_prompt = system_prompt.replace(f"{{{key}}}", value)
                    user_prompt = user_prompt.replace(f"{{{key}}}", value)

                parameters = GenerateTextRequest(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    num_sequences=step_data["parameters"].get("num_sequences", 1),
                    max_tokens=step_data["parameters"].get("max_tokens", 100),
                    temperature=step_data["parameters"].get("temperature", 1.0)
                )
            elif step_data["type"] == "parse":
                parameters = ParseRequest(
                    text=step_data["parameters"].get("text", ""),
                    rules=parse_rules_from_json(step_data["parameters"]["rules"]),
                    output_filter=step_data["parameters"].get("output_filter", "all"),
                    output_limit=step_data["parameters"].get("output_limit", None)
                )
            elif step_data["type"] == "verify":
                methods = parse_verification_methods_from_json(step_data["parameters"]["methods"])
                for method in methods:
                    if isinstance(method.system_prompt, str):
                        for key, value in input_data.items():
                            method.system_prompt = method.system_prompt.replace(f"{{{key}}}", value)
                    if isinstance(method.user_prompt, str):
                        for key, value in input_data.items():
                            method.user_prompt = method.user_prompt.replace(f"{{{key}}}", value)

                parameters = VerifyRequest(
                    methods=methods,
                    required_for_confirmed=step_data["parameters"]["required_for_confirmed"],
                    required_for_review=step_data["parameters"]["required_for_review"]
                )
            else:
                raise ValueError(f"Unknown step type: {step_data['type']}")

            pipeline_steps.append(
                PipelineStep(
                    type=step_data["type"],
                    parameters=parameters,
                    uses_reference=step_data.get("uses_reference", False),
                    reference_step_numbers=step_data.get("reference_step_numbers", [])
                )
            )
        return pipeline_steps

    def _calculate_metrics(self, results: List[Dict[str, Any]]):
        """
        Calcula las métricas de evaluación del benchmark.

        Args:
            results (List[Dict[str, Any]]): Lista de resultados del benchmark.
        """
        correct_predictions = defaultdict(int)
        total_predictions = defaultdict(int)
        misclassified_cases = []

        for result in results:
            actual_label = result["actual_label"]
            predicted_label = result["predicted_label"]

            total_predictions[actual_label] += 1
            if predicted_label == actual_label:
                correct_predictions[actual_label] += 1
            else:
                misclassified_cases.append({
                    "input": result["input"],
                    "expected_output": result["expected_output"],
                    "predicted_label": predicted_label,
                    "actual_label": actual_label
                })

        # Calcular precisión por etiqueta
        accuracy_per_label = {
            label: (correct_predictions[label] / total_predictions[label]) if total_predictions[label] > 0 else 0
            for label in total_predictions
        }

        # Calcular precisión general
        total_correct = sum(correct_predictions.values())
        total = sum(total_predictions.values())
        overall_accuracy = (total_correct / total) if total > 0 else 0

        # Imprimir resultados
        print(f"Precisión general: {overall_accuracy:.2%}")
        for label, accuracy in accuracy_per_label.items():
            print(f"- Precisión para '{label}': {accuracy:.2%}")

        # Guardar casos mal clasificados
        if misclassified_cases:
            save_json_file(misclassified_cases, "misclassified_cases.json")
            print(f"Casos mal clasificados guardados en 'misclassified_cases.json'")