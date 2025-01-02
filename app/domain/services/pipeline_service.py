from typing import Any, Dict, List
from app.domain.model.entities.pipeline import PipelineStep
from app.application.use_cases.generate_text_use_case import GenerateTextUseCase
from app.application.use_cases.parse_generated_output_use_case import ParseGeneratedOutputUseCase
from app.application.use_cases.verify_use_case import VerifyUseCase
from app.domain.services.parse_service import ParseService
from app.domain.services.verifier_service import VerifierService
from app.infrastructure.external.llm.instruct_model import InstructModel

class PipelineService:
    def __init__(self, llm: InstructModel):
        self.llm = llm
        self.reference_data_store: Dict[str, Any] = {}
        self.results: List[Dict[str, Any]] = []

    def run_pipeline(self, steps: List[PipelineStep]):
        for step in steps:
            step_name = step.name
            step_type = step.type
            step_params = step.parameters

            if step.uses_reference:
                # Sustituir placeholders en los prompts usando reference_data_store
                step_params = self._replace_placeholders(step_params, step.reference_step_names)

            if step.uses_verification:
                # Verificar si el paso de verificación previo cumplió con el estado requerido
                if not self._check_verification_status(step.verification_step):
                    continue  # Saltar este paso si la verificación no se cumple

            if step_type == 'generate':
                use_case = GenerateTextUseCase(self.llm)
                response = use_case.execute(step_params)
                self._process_generate_response(response, step_name)
            elif step_type == 'parse':
                parse_service = ParseService()
                use_case = ParseGeneratedOutputUseCase(parse_service)
                response = use_case.execute(step_params)
                self._process_parse_response(response, step_name)
            elif step_type == 'verify':
                verifier_service = VerifierService(self.llm)
                use_case = VerifyUseCase(verifier_service)
                response = use_case.execute(step_params)
                self._process_verify_response(response, step_name)
            else:
                raise ValueError(f"Tipo de paso no reconocido: {step_type}")

    def _replace_placeholders(self, params, reference_step_names):
        # Implementar la lógica para reemplazar placeholders en los prompts
        # Usando los datos de referencia de los pasos especificados en reference_step_names
        pass

    def _check_verification_status(self, verification_status):
        # Implementar la lógica para comprobar el estado de verificación requerido
        pass

    def _process_generate_response(self, response, step_name):
        # Almacenar los resultados de generación y actualizar reference_data_store si necesario
        pass

    def _process_parse_response(self, response, step_name):
        # Almacenar los resultados de análisis y actualizar reference_data_store si necesario
        pass

    def _process_verify_response(self, response, step_name):
        # Almacenar los resultados de verificación y actualizar reference_data_store si necesario
        pass

    def get_results(self):
        return self.results