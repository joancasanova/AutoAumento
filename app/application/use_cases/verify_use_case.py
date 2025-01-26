# application/use_cases/verify_use_case.py

import logging
from datetime import datetime
from domain.model.entities.verification import VerifyRequest, VerifyResponse
from domain.services.verifier_service import VerifierService

logger = logging.getLogger(__name__)

class VerifyUseCase:
    """
    Orchestrates verification processes using multiple validation methods.
    
    Responsibilities:
    - Validates verification request parameters
    - Coordinates verification workflow through VerifierService
    - Calculates performance metrics and success rates
    - Handles error propagation and logging
    
    Uses LLM-based checks to perform:
    - Consensus validation between multiple generations
    - Placeholder verification
    - Semantic consistency checks
    """

    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        Initializes verification components with specified LLM.
        
        Args:
            model_name: Identifier for LLM used in verification generation.
                        Defaults to Qwen2.5-1.5B-Instruct model.
        """
        # Initialize verification service with text generation capability
        self.verifier_service = VerifierService(model_name = model_name)

    def execute(self, request: VerifyRequest) -> VerifyResponse:
        """
        Executes complete verification workflow.
        
        Process Flow:
        1. Validate request parameters
        2. Execute verification methods through service
        3. Calculate performance metrics
        4. Package results with quality indicators
        
        Args:
            request: Contains verification configuration including:
                    - methods: List of verification methods to apply
                    - required_for_confirmed: Threshold for confirmed status
                    - required_for_review: Threshold for review status
        
        Returns:
            VerifyResponse: Contains verification summary and metrics
            
        Raises:
            ValueError: For invalid request parameters
            Exception: Propagates any verification execution errors
        """
        logger.info("Starting verification workflow")
        self._validate_request(request)  # Primary validation
        
        start_time = datetime.now()  # Precision timing started
        
        try:
            logger.debug("Executing %d verification methods", len(request.methods))
            verification_summary = self.verifier_service.verify(
                methods=request.methods,
                required_for_confirmed=request.required_for_confirmed,
                required_for_review=request.required_for_review
            )
            
            # Calculate performance metrics
            execution_time = (datetime.now() - start_time).total_seconds()
            success_rate = verification_summary.success_rate
            
            logger.info("Verification completed in %.4fs (success rate: %.2f)", 
                       execution_time, success_rate)
            
            return VerifyResponse(
                verification_summary=verification_summary,
                execution_time=execution_time,
                success_rate=success_rate
            )
            
        except Exception as e:
            logger.error("Critical error during verification process")
            # Preserve stack trace while propagating error
            raise e

    def _validate_request(self, request: VerifyRequest) -> None:
        """
        Ensures verification request meets operational constraints.
        
        Validation Rules:
        1. At least one verification method required
        2. Confirmed threshold must be positive
        3. Review threshold must be positive
        4. Confirmed threshold > Review threshold
        5. Method-level validation:
           - Required matches must be positive
           - Required matches <= num_sequences
        
        Args:
            request: Verification request to validate
            
        Raises:
            ValueError: With detailed message about validation failure
        """
        logger.debug("Validating verification request parameters")
        
        # Global parameter validation
        if not request.methods:
            logger.error("Missing verification methods")
            raise ValueError("At least one verification method required")
            
        if request.required_for_confirmed <= 0:
            raise ValueError("Confirmed threshold must be positive")
            
        if request.required_for_review <= 0:
            raise ValueError("Review threshold must be positive")
            
        if request.required_for_confirmed <= request.required_for_review:
            raise ValueError("Confirmed threshold must exceed review threshold")

        # Per-method validation
        for method in request.methods:
            if method.required_matches is None:
                continue
                
            if method.required_matches <= 0:
                raise ValueError(f"{method.name}: Required matches must be positive")
                
            if method.required_matches > method.num_sequences:
                raise ValueError(
                    f"{method.name}: Required matches ({method.required_matches}) "
                    f"exceed available sequences ({method.num_sequences})"
                )