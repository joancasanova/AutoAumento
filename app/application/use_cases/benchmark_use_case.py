from copy import deepcopy
from typing import List, Dict, Any
import json
from datetime import datetime

from domain.model.entities.pipeline import PipelineStep, PipelineRequest
from domain.model.entities.generation import GenerateTextRequest
from domain.model.entities.parsing import ParseRequest
from domain.model.entities.verification import VerifyRequest, VerificationMethod
from application.use_cases.pipeline_use_case import PipelineUseCase


class BenchmarkUseCase:
    """
    Caso de uso para ejecutar benchmarks del pipeline con diferentes entradas
    y calcular métricas de rendimiento.
    """

    def __init__(
        self,
        model_name: str,
        pipeline_steps: List[PipelineStep],
        benchmark_entries: List[Dict[str, Any]],
        label_key: str,
        label_value: str
    ):
        """
        Args:
            model_name: Nombre del modelo a utilizar
            pipeline_steps: Lista de pasos del pipeline configurado
            benchmark_entries: Lista de entradas para el benchmark
            label_key: Clave que identifica la etiqueta verdadera en los datos
            label_value: Valor que se considera como clase positiva
        """
        self.model_name = model_name
        self.original_steps = pipeline_steps
        self.benchmark_entries = benchmark_entries
        self.label_key = label_key
        self.label_value = label_value

    def run_benchmark(self):
        """Ejecuta el benchmark completo y muestra los resultados."""
        results = []
        
        for entry in self.benchmark_entries:
            # Extraer datos de entrada y etiqueta verdadera
            input_data = {k: v for k, v in entry.items() if k != self.label_key}
            expected_label = entry.get(self.label_key, "")

            # Configurar y ejecutar pipeline
            pipeline_response = self._execute_pipeline_for_entry(input_data)
            
            # Procesar resultados
            prediction_result = self._process_prediction(
                pipeline_response, 
                input_data,
                expected_label
            )
            
            if prediction_result:
                results.append(prediction_result)

        # Calcular y mostrar métricas
        self._calculate_and_display_metrics(results)

    def _execute_pipeline_for_entry(self, input_data: Dict) -> Any:
        """Ejecuta el pipeline para una entrada específica."""
        try:
            # Clonar y configurar pasos
            configured_steps = self._configure_pipeline_steps(input_data)
            
            # Ejecutar pipeline
            pipeline = PipelineUseCase(self.model_name)
            return pipeline.execute(
                PipelineRequest(
                    steps=configured_steps,
                    global_references=input_data
                )
            )
        except Exception as e:
            print(f"Error ejecutando pipeline: {str(e)}")
            return None

    def _configure_pipeline_steps(self, entry_data: Dict) -> List[PipelineStep]:
        """Clona y configura los pasos del pipeline con los datos de entrada."""
        configured_steps = []
        
        for step in self.original_steps:
            try:
                # Clonar el paso para evitar modificar el original
                cloned_step = deepcopy(step)
                
                # Sustituir placeholders en los parámetros
                self._substitute_placeholders(
                    cloned_step.parameters, 
                    entry_data
                )
                
                configured_steps.append(cloned_step)
            except Exception as e:
                print(f"Error configurando paso {step.step_type}: {str(e)}")
        
        return configured_steps

    def _substitute_placeholders(self, parameters: Any, data: Dict):
        """Reemplaza placeholders en los parámetros del paso."""
        if isinstance(parameters, GenerateTextRequest):
            parameters.system_prompt = self._replace_in_template(
                parameters.system_prompt, 
                data
            )
            parameters.user_prompt = self._replace_in_template(
                parameters.user_prompt, 
                data
            )
        
        elif isinstance(parameters, ParseRequest):
            parameters.text = self._replace_in_template(
                parameters.text, 
                data
            )
        
        elif isinstance(parameters, VerifyRequest):
            for method in parameters.methods:
                method.system_prompt = self._replace_in_template(
                    method.system_prompt, 
                    data
                )
                method.user_prompt = self._replace_in_template(
                    method.user_prompt, 
                    data
                )

    def _replace_in_template(self, template: str, data: Dict) -> str:
        """Reemplaza placeholders del tipo {key} en un template."""
        if not template:
            return template
            
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in template:
                template = template.replace(
                    placeholder, 
                    str(value)
                )
        return template

    def _process_prediction(
        self, 
        pipeline_response: Any,
        input_data: Dict,
        expected_label: str
    ) -> Dict:
        """Extrae y procesa los resultados de verificación."""
        if not pipeline_response:
            return None

        # Buscar resultados de verificación
        verify_step = next(
            (s for s in pipeline_response.step_results 
             if s["step_type"] == "verify"),
            None
        )
        
        if not verify_step or not verify_step["step_data"]:
            return None

        # Obtener resumen de verificación
        verify_summary = verify_step["step_data"][-1]
        
        return {
            "input": input_data,
            "predicted_label": self._determine_label(verify_summary),
            "actual_label": expected_label,
            "timestamp": datetime.now().isoformat()
        }

    def _determine_label(self, verify_summary: Dict) -> str:
        """Determina la etiqueta predicha basada en el resumen de verificación."""
        status = verify_summary.get("final_status", "").lower()
        return "confirmed" if status == "confirmed" else "not_confirmed"

    def _calculate_and_display_metrics(self, results: List[Dict]):
        """Calcula y muestra las métricas principales."""
        if not results:
            print("No se obtuvieron resultados para calcular métricas")
            return

        # Contadores iniciales
        correct = 0
        total = len(results)
        confusion_matrix = {
            "true_positive": 0,
            "false_positive": 0,
            "true_negative": 0,
            "false_negative": 0
        }

        # Clasificar resultados
        misclassified = []
        for result in results:
            actual = result["actual_label"]
            predicted = result["predicted_label"]
            
            is_actual_positive = (actual == self.label_value)
            is_predicted_positive = (predicted == "confirmed")

            if is_actual_positive and is_predicted_positive:
                confusion_matrix["true_positive"] += 1
                correct += 1
            elif not is_actual_positive and not is_predicted_positive:
                confusion_matrix["true_negative"] += 1
                correct += 1
            elif is_actual_positive and not is_predicted_positive:
                confusion_matrix["false_negative"] += 1
                misclassified.append(result)
            else:
                confusion_matrix["false_positive"] += 1
                misclassified.append(result)

        # Calcular métricas
        accuracy = correct / total
        precision = confusion_matrix["true_positive"] / (
            confusion_matrix["true_positive"] + confusion_matrix["false_positive"] + 1e-10
        )
        recall = confusion_matrix["true_positive"] / (
            confusion_matrix["true_positive"] + confusion_matrix["false_negative"] + 1e-10
        )
        f1 = 2 * (precision * recall) / (precision + recall + 1e-10)

        # Mostrar resultados
        print("\n=== Resultados del Benchmark ===")
        print(f"• Exactitud (Accuracy): {accuracy:.2%}")
        print(f"• Precisión: {precision:.2%}")
        print(f"• Sensibilidad (Recall): {recall:.2%}")
        print(f"• F1-Score: {f1:.2%}")
        print("\nMatriz de Confusión:")
        print(f"Verdaderos Positivos: {confusion_matrix['true_positive']}")
        print(f"Falsos Positivos: {confusion_matrix['false_positive']}")
        print(f"Verdaderos Negativos: {confusion_matrix['true_negative']}")
        print(f"Falsos Negativos: {confusion_matrix['false_negative']}")

        # Guardar casos problemáticos
        if misclassified:
            self._save_misclassified(misclassified)

    def _save_misclassified(self, cases: List[Dict]):
        """Guarda casos mal clasificados en un archivo JSON."""
        filename = f"misclassified_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(cases, f, indent=2, ensure_ascii=False)
            print(f"\nSe guardaron {len(cases)} casos mal clasificados en {filename}")
        except Exception as e:
            print(f"\nError guardando casos mal clasificados: {str(e)}")