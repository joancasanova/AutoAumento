# application/use_cases/verification/verify_text_use_case.py

import logging
from datetime import datetime
from domain.model.entities.verification import VerifyRequest, VerifyResponse
from domain.services.verifier_service import VerifierService

logger = logging.getLogger(__name__)

class VerifyUseCase:
    """
    Use case for verifying text or data using one or more verification methods.
    These methods rely on LLM-based checks (consensus checks, placeholders, etc.).
    """
    def __init__(self, verifier_service: VerifierService):
        self.verifier_service = verifier_service

    def execute(self, request: VerifyRequest) -> VerifyResponse:
        """
        Execute the verification:
         1) Validate the request input.
         2) Perform the verification process via the VerifierService.
         3) Return the final verification response and summary.
        """
        logger.info("Executing VerifyUseCase")
        self._validate_request(request)
        
        start_time = datetime.now()
        
        try:
            logger.debug("Invoking the verifier service.")
            verification_summary = self.verifier_service.verify(
                methods=request.methods,
                required_for_confirmed=request.required_for_confirmed,
                required_for_review=request.required_for_review,
                reference_data=request.reference_data
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            success_rate = verification_summary.success_rate
            
            logger.info(f"Verification completed in {execution_time:.4f}s with success rate {success_rate:.2f}")
            return VerifyResponse(
                verification_summary=verification_summary,
                execution_time=execution_time,
                success_rate=success_rate
            )
            
        except Exception as e:
            logger.exception("Error during verification.")
            raise e
        
    def _validate_request(self, request: VerifyRequest) -> None:
        """
        Validates the verification request:
         - Must provide at least one verification method.
         - The threshold required_for_confirmed must be > 0.
         - The threshold required_for_review must be > 0.
         - required_for_confirmed must be strictly greater than required_for_review.
         - Each verification method's required_matches must be positive and not exceed num_sequences.
        """
        logger.debug("Validating verify request parameters.")
        if not request.methods:
            logger.error("At least one verification method must be provided.")
            raise ValueError("At least one verification method must be provided.")
        if request.required_for_confirmed <= 0:
            logger.error("required_for_confirmed must be positive.")
            raise ValueError("required_for_confirmed must be positive.")
        if request.required_for_review <= 0:
            logger.error("required_for_review must be positive.")
            raise ValueError("required_for_review must be positive.")
        if request.required_for_confirmed <= request.required_for_review:
            logger.error("required_for_confirmed must be greater than required_for_review.")
            raise ValueError("required_for_confirmed must be greater than required_for_review")

        for method in request.methods:
            if method.required_matches is not None:
                if method.required_matches <= 0:
                    logger.error(f"Method '{method.name}': required_matches must be positive.")
                    raise ValueError(f"Method '{method.name}': required_matches must be positive")
                if method.required_matches > method.num_sequences:
                    logger.error(
                        f"Method '{method.name}': required_matches ({method.required_matches}) "
                        f"cannot be greater than num_sequences ({method.num_sequences})"
                    )
                    raise ValueError(
                        f"Method '{method.name}': required_matches ({method.required_matches}) "
                        f"cannot be greater than num_sequences ({method.num_sequences})"
                    )
