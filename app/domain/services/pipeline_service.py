# app/domain/services/pipeline_service.py

import logging
from typing import Any, Dict, List, Optional, Union
import json
import copy

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
    VerificationMode,
    VerifyResponse
)
from app.domain.model.entities.pipeline import PipelineStep

logger = logging.getLogger(__name__)

class PipelineService:
    """
    PipelineService maneja la ejecución secuencial de los pasos en un pipeline.
    Cada paso puede ser 'generate', 'parse', o 'verify', y toma la
    salida del paso previo como su entrada.

    Almacena los resultados intermedios de cada paso y permite exportarlos a JSON.
    """

    def __init__(self, llm: InstructModel):
        """
        Inicializa el PipelineService.

        Args:
            llm (InstructModel): Modelo LLM pre-instanciado para generación de texto.
        """
        self.llm = llm
        self.reference_data_store: Dict[str, Any] = {}
        self.intermediate_results: List[Dict[str, Any]] = []
        logger.debug("PipelineService inicializado.")

    def run_pipeline(self, steps: List[PipelineStep], parameters: Dict[str, Any]):
        logger.info("Ejecutando el pipeline completo.")
        self.intermediate_results = []
        current_inputs: List[Any] = [None]  # Input inicial sigue siendo None
        execution_order = 1

        for step in steps:
            step_name = step.name
            step_type = step.type
            step_params = parameters.get(step_name)

            if not step_params:
                logger.error(f"No se encontraron parámetros para el paso '{step_name}'.")
                raise ValueError(f"Faltan parámetros para el paso '{step_name}'.")

            logger.info(f"Ejecutando paso: {step_name} (tipo: {step_type}, orden: {execution_order})")

            if execution_order == 1 and step_type != "generate":
                # Si es el primer paso y no es 'generate', obtenemos la entrada del input_data del step.
                # En cualquier otro caso, la entrada será la salida del paso anterior
                current_input = step_params.get("input_data")
            else:
                current_input = current_inputs[0] if step_type == "generate" else current_inputs
            
            if step_type == "generate":
                # Si es 'generate', usamos current_inputs[0] (que será None para la primera ejecución)
                try:
                    request = self._prepare_request(step_type, step_params, execution_order, None) # Input data será None
                    output_items = self.run_pipeline_step(
                        step_type=step_type,
                        request=request,
                        input_data=None, # Input data será None
                        step_name=step_name,
                        execution_order=execution_order,
                    )

                    # Almacenar resultados intermedios
                    self.add_intermediate_result(step_name, step_type, execution_order, request, output_items)
                    
                    # Actualizar current_inputs con la salida del paso 'generate'
                    current_inputs = output_items

                except Exception as e:
                    logger.error(f"Error al ejecutar el paso {step_name}: {e}")
                    raise

            elif step_type in ["parse", "verify"]:
                # Para 'parse' y 'verify', iteramos sobre los inputs actuales
                step_outputs = []

                # Si es el primer paso, desempaquetamos input_data para la iteración.
                if execution_order == 1:
                    current_inputs = [current_input]

                for current_input in current_inputs:
                    try:
                        request = self._prepare_request(step_type, step_params, execution_order, current_input)
                        output_items = self.run_pipeline_step(
                            step_type=step_type,
                            request=request,
                            input_data=current_input,
                            step_name=step_name,
                            execution_order=execution_order,
                        )

                        # Formatear la salida de verify para mayor consistencia
                        if step_type == 'verify':
                            output_items = [
                                {
                                    "final_status": output.verification_summary.final_status,
                                    "success_rate": output.success_rate,
                                    "execution_time": output.execution_time,
                                    "details": [
                                        {
                                            "method_name": result.method.name,
                                            "mode": result.method.mode.value,
                                            "passed": result.passed,
                                            "score": result.score,
                                            "timestamp": result.timestamp.isoformat(),
                                            "details": result.details
                                        }
                                        for result in output.verification_summary.results
                                    ]
                                }
                                for output in output_items
                            ]

                        step_outputs.extend(output_items)
                        # Almacenar resultados intermedios
                        self.add_intermediate_result(step_name, step_type, execution_order, current_input, output_items)

                    except Exception as e:
                        logger.error(f"Error al ejecutar el paso {step_name}: {e}")
                        raise
                
                current_inputs = step_outputs  # Actualizar current_inputs para el siguiente paso
            else:
                logger.warning(f"Tipo de paso desconocido '{step_type}'. Saltando.")

            execution_order += 1
        logger.info("Pipeline completado.")

    def run_pipeline_step(
        self,
        step_type: str,
        request: Any,
        step_name: str,
        execution_order: int,
    ) -> List[Any]:
        """
        Ejecuta un solo paso del pipeline.

        Args:
            step_type: Tipo de paso ('generate', 'parse', 'verify').
            request: Instancia de la dataclass de request adecuada para el paso actual.
            input_data: Datos de entrada del paso anterior.
            step_name: Nombre del paso actual.
            execution_order: Orden de ejecución del paso actual.

        Returns:
            Lista de outputs del paso.
        """
        logger.info(f"Ejecutando '{step_type}' para el paso '{step_name}'.")

        if step_type == "generate":
            return self._run_generate(request)
        elif step_type == "parse":
            outputs = self._run_parse(request)
            self.reference_data_store[f"parse_step_{execution_order}"] = outputs
            return outputs
        elif step_type == "verify":
            return self._run_verify(request)
        else:
            logger.warning(f"Tipo de paso desconocido '{step_type}'. Saltando.")
            return []

    def _run_generate(self, request: GenerateTextRequest) -> List[str]:
        """
        Ejecuta el paso 'generate'.

        Args:
            request: GenerateTextRequest con los parámetros del paso.

        Returns:
            Lista de textos generados.
        """
        logger.info("Ejecutando paso 'generate'.")

        generate_use_case = GenerateTextUseCase(self.llm)
        response = generate_use_case.execute(request)
        return [gen_result.content for gen_result in response.generated_texts]

    def _run_parse(self, request: ParseRequest) -> List[Dict[str, str]]:
        """
        Ejecuta el paso 'parse'.

        Args:
            request: ParseRequest con los parámetros del paso.

        Returns:
            Lista de diccionarios con los resultados del análisis.
        """
        logger.info("Ejecutando paso 'parse'.")

        parse_service = ParseService()
        parse_use_case = ParseGeneratedOutputUseCase(parse_service)

        parse_response = parse_use_case.execute(request)
        return parse_response.parse_result.entries

    def _run_verify(self, request: VerifyRequest) -> List[VerifyResponse]:
        """
        Ejecuta el paso 'verify'.

        Args:
            request: VerifyRequest con los parámetros del paso.

        Returns:
            Lista de VerifyResponse, una para cada ejecución de verificación.
        """
        logger.info("Ejecutando paso 'verify'.")

        verifier_service = VerifierService(self.llm)
        verify_use_case = VerifyUseCase(verifier_service)

        # Pasar cada input al verify use case y recoger las respuestas
        verify_responses: List[VerifyResponse] = []

        response = verify_use_case.execute(request)
        verify_responses.append(response)
        
        return verify_responses

    def _get_reference_data(self, reference_data_source: Optional[str], execution_order: int, step_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene los datos de referencia según la fuente especificada."""
        if reference_data_source == "global":
            reference_data = self.reference_data_store.get("global")
            if not reference_data:
                logger.error("Datos de referencia globales no proporcionados.")
                raise ValueError("Datos de referencia globales no proporcionados.")
        elif reference_data_source and reference_data_source.startswith("parse_step_"):
            try:
                parse_step_number = int(reference_data_source.split("_")[-1])
            except ValueError:
                logger.error(f"Fuente de datos de referencia inválida '{reference_data_source}'. Debe ser 'global' o 'parse_step_<número>'.")
                raise ValueError(f"Fuente de datos de referencia inválida '{reference_data_source}'. Debe ser 'global' o 'parse_step_<número>'.")
            if parse_step_number >= execution_order:
                logger.error(f"La fuente de datos de referencia '{reference_data_source}' debe referirse a un paso de análisis anterior al paso actual.")
                raise ValueError(f"La fuente de datos de referencia '{reference_data_source}' debe referirse a un paso de análisis anterior al paso actual.")
            reference_data = self.reference_data_store.get(reference_data_source)
            if not reference_data:
                logger.error(f"Datos de referencia '{reference_data_source}' no encontrados.")
                raise ValueError(f"Datos de referencia '{reference_data_source}' no encontrados.")
        else:
            reference_data = None
        return reference_data
    
    def _prepare_request(self, step_type: str, step_params: Dict[str, Any], execution_order: int, input_data: Optional[Any] = None) -> Union[GenerateTextRequest, ParseRequest, VerifyRequest]:
        """
        Prepara la dataclass de request adecuada para el paso actual, a partir de la configuración en formato JSON.

        Args:
            step_type: Tipo de paso.
            step_params: Diccionario con los parámetros del paso, tal como viene del JSON.
            execution_order: Orden de ejecución del paso actual.
            input_data: Datos de entrada del paso anterior (opcional).

        Returns:
            Instancia de la dataclass de request adecuada.
        """
        reference_data_source = step_params.get("reference_data_source")
        reference_data = self._get_reference_data(reference_data_source, execution_order, "current_step_name")
        
        if step_type == "generate":
            gen_params = step_params.get("generate_request", {})
            return GenerateTextRequest(
                system_prompt=gen_params.get("system_prompt"),
                user_prompt=gen_params.get("user_prompt"),
                num_sequences=gen_params.get("num_sequences", 1),
                max_tokens=gen_params.get("max_tokens", 50),
                temperature=gen_params.get("temperature", 1.0),
                reference_data=reference_data
            )
        elif step_type == "parse":
            parse_params = step_params.get("parse_request", {})
            
            rules_data = parse_params.get("rules", [])
            rules = []
            for rule_data in rules_data:
                try:
                    mode = ParseMode(rule_data["mode"].lower())
                    rule = ParseRule(
                        name=rule_data["name"],
                        pattern=rule_data["pattern"],
                        mode=mode,
                        secondary_pattern=rule_data.get("secondary_pattern"),
                        fallback_value=rule_data.get("fallback_value")
                    )
                    rules.append(rule)
                except (KeyError, ValueError) as e:
                    logger.error(f"Error en la definición de la regla: {e}")
                    raise
            
            return ParseRequest(
                text= input_data if execution_order > 1 else parse_params.get("text"),
                rules=rules,
                output_filter=parse_params.get("output_filter", "all"),
                output_limit=parse_params.get("output_limit")
            )
        elif step_type == "verify":
            verify_params = step_params.get("verify_request", {})
            
            methods_data = verify_params.get("methods", [])
            methods = []
            for method_data in methods_data:
                try:
                    mode = VerificationMode(method_data["mode"].upper())
                    method = VerificationMethod(
                        mode=mode,
                        name=method_data["name"],
                        system_prompt=method_data["system_prompt"],
                        user_prompt=method_data["user_prompt"],
                        valid_responses=method_data["valid_responses"],
                        num_sequences=method_data.get("num_sequences", 3),
                        required_matches=method_data.get("required_matches", 2)
                    )
                    methods.append(method)
                except (KeyError, ValueError) as e:
                    logger.error(f"Error en la definición del método de verificación: {e}")
                    raise

            return VerifyRequest(
                methods=methods,
                required_for_confirmed=verify_params.get("required_for_confirmed"),
                required_for_review=verify_params.get("required_for_review"),
                reference_data=reference_data if reference_data else input_data
            )
        else:
            raise ValueError(f"Tipo de paso desconocido: {step_type}")
        
    def add_intermediate_result(
        self,
        step_name: str,
        step_type: str,
        execution_order: int,
        input_data: Any,
        output_data: Any
    ):
        """Añade un resultado intermedio a la lista de resultados."""
        if step_type == "generate":
            input_data = {"system_prompt": input_data.system_prompt, "user_prompt": input_data.user_prompt}
        
        step_result = {
            "step_name": step_name,
            "step_type": step_type,
            "execution_order": execution_order,
            "results": [
                {
                    "input": input_data,
                    "output": output_data
                }
            ]
        }

        # Buscar si ya existe un paso con el mismo nombre y orden de ejecución
        existing_step_index = next((i for i, step in enumerate(self.intermediate_results) if step["step_name"] == step_name and step["execution_order"] == execution_order), None)

        if existing_step_index is not None:
            # Si existe, añadir los resultados al paso existente
            self.intermediate_results[existing_step_index]["results"].extend(step_result["results"])
        else:
            # Si no existe, añadir el nuevo paso a la lista
            self.intermediate_results.append(step_result)

    def get_intermediate_results(self) -> List[Dict[str, Any]]:
        """Devuelve una copia de los resultados intermedios del pipeline."""
        return copy.deepcopy(self.intermediate_results)

    def export_results_to_json(self, filepath: str):
        """Exporta los resultados del pipeline a un archivo JSON."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.intermediate_results, f, indent=2, ensure_ascii=False)