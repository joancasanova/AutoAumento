# app/domain/services/pipeline_service.py

import logging
from typing import Any, Dict, List, Optional
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

    def run_pipeline(self, steps: List[Dict[str, str]], parameters: Dict[str, Dict[str, Any]]):
        """
        Ejecuta un pipeline completo, paso a paso.

        Args:
            steps: Lista de pasos del pipeline.
            parameters: Diccionario con los parámetros para cada paso.
        """
        logger.info("Ejecutando el pipeline completo.")
        self.intermediate_results = []  # Resetear resultados intermedios
        current_inputs: List[Any] = [None]  # Input inicial es None
        execution_order = 1

        for step in steps:
            step_name = step.name  # Acceder al atributo name usando notación de punto
            step_type = step.type  # Acceder al atributo type usando notación de punto
            step_params = parameters.get(step_name)

            if not step_params:
                logger.error(f"No se encontraron parámetros para el paso '{step_name}'.")
                raise ValueError(f"Faltan parámetros para el paso '{step_name}'.")

            logger.info(f"Ejecutando paso: {step_name} (tipo: {step_type}, orden: {execution_order})")

            step_outputs = []
            for current_input in current_inputs:
                try:
                    output_items = self.run_pipeline_step(
                        step_type=step_type,
                        params=step_params,
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

            current_inputs = step_outputs
            execution_order += 1

        logger.info("Pipeline completado.")

    def run_pipeline_step(
        self,
        step_type: str,
        params: Dict[str, Any],
        input_data: Any,
        step_name: str,
        execution_order: int,
    ) -> List[Any]:
        """
        Ejecuta un solo paso del pipeline.

        Args:
            step_type: Tipo de paso ('generate', 'parse', 'verify').
            params: Parámetros para el paso.
            input_data: Datos de entrada del paso anterior.
            step_name: Nombre del paso actual.
            execution_order: Orden de ejecución del paso actual.

        Returns:
            Lista de outputs del paso.
        """
        logger.info(f"Ejecutando '{step_type}' para el paso '{step_name}'.")

        reference_data_source = params.get("reference_data_source")
        reference_data = self._get_reference_data(reference_data_source, execution_order, step_name)

        if step_type == "generate":
            return self._run_generate(params, reference_data, input_data)
        elif step_type == "parse":
            outputs = self._run_parse(params, input_data)
            self.reference_data_store[f"parse_step_{execution_order}"] = outputs
            return outputs
        elif step_type == "verify":
            return self._run_verify(params, input_data, reference_data)
        else:
            logger.warning(f"Tipo de paso desconocido '{step_type}'. Saltando.")
            return []

    def _get_reference_data(self, reference_data_source: Optional[str], execution_order: int, step_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene los datos de referencia según la fuente especificada."""
        if reference_data_source == "global":
            if execution_order != 1:
                logger.error("Los datos de referencia globales solo se pueden usar en el primer paso.")
                raise ValueError("Los datos de referencia globales solo se pueden usar en el primer paso.")
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

    def _run_generate(self, params: Dict[str, Any], reference_data: Optional[Dict[str, Any]], input_data: Any) -> List[str]:
        """
        Ejecuta el paso 'generate'.

        Args:
            params: Parámetros para el paso.
            reference_data: Datos de referencia para placeholders.
            input_data: Datos de entrada del paso anterior (ignorados en generate).

        Returns:
            Lista de textos generados.
        """
        logger.info("Ejecutando paso 'generate'.")

        system_prompt = params["system_prompt"]
        user_prompt = params["user_prompt"]
        num_sequences = params.get("num_sequences", 1)
        max_tokens = params.get("max_tokens", 50)
        temperature = params.get("temperature", 1.0)

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
        return [gen_result.content for gen_result in response.generated_texts]

    def _run_parse(self, params: Dict[str, Any], text_to_parse: str) -> List[Dict[str, str]]:
        """
        Ejecuta el paso 'parse'.

        Args:
            params: Parámetros para el paso.
            text_to_parse: Texto a analizar.

        Returns:
            Lista de diccionarios con los resultados del análisis.
        """
        logger.info("Ejecutando paso 'parse'.")

        if not text_to_parse:
            logger.warning("No hay texto de entrada para el paso 'parse'.")
            return []

        rules_file = params["rules_file"]
        output_filter = params.get("output_filter", "all")
        output_limit = params.get("output_limit")

        try:
            with open(rules_file, "r", encoding="utf-8") as f:
                rules_data = json.load(f)
        except Exception as e:
            logger.error(f"Error al cargar el archivo de reglas '{rules_file}': {e}")
            raise

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
                logger.error(f"Clave faltante en el archivo de reglas: {e}")
                raise
            except ValueError as e:
                logger.error(f"Modo inválido en el archivo de reglas: {e}")
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

        return parse_response.parse_result.entries

    def _run_verify(
        self,
        params: Dict[str, Any],
        input_item: Any,
        reference_data: Optional[Dict[str, Any]],
    ) -> List[VerifyResponse]:
        """
        Ejecuta el paso 'verify'.

        Args:
            params: Parámetros para el paso.
            input_item: Elemento de entrada del paso anterior.
            reference_data: Datos de referencia para placeholders.

        Returns:
            Lista de VerifyResponse, una para cada ejecución de verificación.
        """
        logger.info("Ejecutando paso 'verify'.")
        
        if input_item is None:
            logger.warning("No hay elemento de entrada para el paso 'verify'.")
            return []

        methods_file = params["methods_file"]
        required_confirmed = params["required_confirmed"]
        required_review = params["required_review"]

        try:
            with open(methods_file, "r", encoding="utf-8") as f:
                methods_data = json.load(f)
        except Exception as e:
            logger.error(f"Error al cargar el archivo de métodos '{methods_file}': {e}")
            raise

        methods_list = []
        for m in methods_data:
            try:
                mode = VerificationMode(m["mode"].upper())
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
                logger.error(f"Clave faltante en el archivo de métodos: {e}")
                raise
            except ValueError as e:
                logger.error(f"Modo inválido en el archivo de métodos: {e}")
                raise

        verifier_service = VerifierService(self.llm)
        verify_use_case = VerifyUseCase(verifier_service)

        verify_request = VerifyRequest(
            methods=methods_list,
            required_for_confirmed=required_confirmed,
            required_for_review=required_review,
            reference_data=reference_data if reference_data else None
        )

        # Pasar cada input al verify use case y recoger las respuestas
        verify_responses: List[VerifyResponse] = []
        if isinstance(input_item, list):
            for item in input_item:
                verify_request.reference_data=item
                response = verify_use_case.execute(verify_request)
                verify_responses.append(response)
        else:
            verify_request.reference_data = input_item
            response = verify_use_case.execute(verify_request)
            verify_responses.append(response)
        
        return verify_responses

    def add_intermediate_result(
        self,
        step_name: str,
        step_type: str,
        execution_order: int,
        input_data: Any,
        output_data: Any
    ):
        """Añade un resultado intermedio a la lista de resultados."""
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