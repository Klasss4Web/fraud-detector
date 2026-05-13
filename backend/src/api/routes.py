"""
FastAPI routes for the Fraud Detection API.
"""

import time
from typing import Any
from fastapi import APIRouter, HTTPException, Depends

from api.models import (
    TransactionRequest,
    InsuranceClaimRequest,
    UserProfileRequest,
    EcommerceOrderRequest,
    ComprehensiveRequest,
    BatchAnalysisRequest,
    FraudAnalysisResponse,
    FraudSignalResponse,
    BatchAnalysisResponse,
    HealthResponse,
    DependencyHealth,
    EntityTypeEnum,
    DetectionScoreRequest,
    DetectionScoreResponse,
    MixedDetectionRequest,
    MixedDetectionResponse,
)
from api.config import Settings, get_settings
from orchestrator import FraudDetectionOrchestrator, EntityType

router = APIRouter()

# Global orchestrator instance (initialized on startup)
_orchestrator: FraudDetectionOrchestrator | None = None
_startup_time: float = time.time()


def get_orchestrator() -> FraudDetectionOrchestrator:
    """Dependency to get the orchestrator instance."""
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return _orchestrator


def init_orchestrator(settings: Settings) -> None:
    """Initialize the global orchestrator."""
    global _orchestrator
    _orchestrator = FraudDetectionOrchestrator(
        enable_llm=settings.enable_llm and settings.openai_api_key is not None,
        openai_api_key=settings.openrouter_api_key,
        auto_investigate_threshold=settings.auto_investigate_threshold,
        enable_ml=settings.enable_ml,
        ml_model_name=settings.ml_model_name,
    )


def _convert_result_to_response(result: Any) -> FraudAnalysisResponse:
    """Convert FraudAnalysisResult to FraudAnalysisResponse."""
    return FraudAnalysisResponse(
        entity_id=result.entity_id,
        entity_type=result.entity_type,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        requires_action=result.requires_action,
        recommendation=result.recommendation,
        signals=[
            FraudSignalResponse(
                name=s["name"],
                description=s["description"],
                weight=s["weight"],
                category=s["category"],
            )
            for s in result.signals
        ],
        agent_results=result.agent_results,
        investigation_report=result.investigation_report,
    )


# ============== Health Check ==============


def _check_database_health() -> DependencyHealth:
    """Check PostgreSQL database health."""
    try:
        from db.session import check_database_health

        start = time.time()
        result = check_database_health()
        latency = (time.time() - start) * 1000

        return DependencyHealth(
            status=result.get("status", "unknown"),
            latency_ms=round(latency, 2),
            error=result.get("error"),
        )
    except ImportError:
        return DependencyHealth(status="unavailable", error="Database module not installed")
    except Exception as e:
        return DependencyHealth(status="unhealthy", error=str(e))


def _check_redis_health() -> DependencyHealth:
    """Check Redis cache health."""
    try:
        from db.session import check_redis_health

        start = time.time()
        result = check_redis_health()
        latency = (time.time() - start) * 1000

        return DependencyHealth(
            status=result.get("status", "unknown"),
            latency_ms=round(latency, 2),
            error=result.get("error") or result.get("reason"),
        )
    except ImportError:
        return DependencyHealth(status="unavailable", error="Redis module not installed")
    except Exception as e:
        return DependencyHealth(status="unhealthy", error=str(e))


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Check API health and status.

    Returns overall health status and individual dependency health:
    - **healthy**: All systems operational
    - **degraded**: Core functionality works but some dependencies are down
    - **unhealthy**: Critical systems are down
    """
    agents = [
        "TransactionFraudAgent",
        "InsuranceFraudAgent",
        "IdentityFraudAgent",
        "EcommerceFraudAgent",
        "RiskScoringAgent",
    ]
    if settings.enable_llm and settings.openai_api_key:
        agents.append("InvestigationAgent")

    # Check dependencies
    db_health = _check_database_health()
    redis_health = _check_redis_health()

    dependencies = {
        "database": db_health,
        "cache": redis_health,
    }

    # Determine overall status
    # - healthy: all dependencies healthy or unavailable (optional)
    # - degraded: some dependencies unhealthy but core works
    # - unhealthy: critical dependency down
    db_ok = db_health.status in ("healthy", "unavailable")
    redis_ok = redis_health.status in ("healthy", "unavailable")

    if db_ok and redis_ok:
        overall_status = "healthy"
    elif db_health.status == "unhealthy":
        overall_status = "degraded"  # DB down but API can still work in memory mode
    else:
        overall_status = "degraded"

    uptime = time.time() - _startup_time

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        agents_loaded=agents,
        dependencies=dependencies,
        uptime_seconds=round(uptime, 2),
    )


# ============== Transaction Analysis ==============


@router.post(
    "/analyze/transaction",
    response_model=FraudAnalysisResponse,
    tags=["Analysis"],
    summary="Analyze a financial transaction for fraud",
)
async def analyze_transaction(
    request: TransactionRequest,
    auto_investigate: bool = True,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Analyze a financial transaction for potential fraud.

    This endpoint uses the Transaction Fraud Agent to detect:
    - Velocity attacks (rapid transactions)
    - Amount anomalies
    - Geographic risks
    - Device/IP patterns
    - Time-based patterns
    """
    try:
        result = orchestrator.analyze_transaction(
            transaction_data=request.model_dump(),
            auto_investigate=auto_investigate,
        )
        return _convert_result_to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Insurance Claim Analysis ==============


@router.post(
    "/analyze/insurance-claim",
    response_model=FraudAnalysisResponse,
    tags=["Analysis"],
    summary="Analyze an insurance claim for fraud",
)
async def analyze_insurance_claim(
    request: InsuranceClaimRequest,
    auto_investigate: bool = True,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Analyze an insurance claim for potential fraud.

    This endpoint uses the Insurance Fraud Agent to detect:
    - Staged incidents
    - Exaggerated claims
    - Serial claimants
    - Policy timing fraud
    - Suspicious descriptions
    """
    try:
        result = orchestrator.analyze_insurance_claim(
            claim_data=request.model_dump(),
            auto_investigate=auto_investigate,
        )
        return _convert_result_to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== User Profile Analysis ==============


@router.post(
    "/analyze/user-profile",
    response_model=FraudAnalysisResponse,
    tags=["Analysis"],
    summary="Analyze a user profile for identity fraud",
)
async def analyze_user_profile(
    request: UserProfileRequest,
    auto_investigate: bool = True,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Analyze a user profile for identity fraud.

    This endpoint uses the Identity Fraud Agent to detect:
    - Synthetic identity fraud
    - Account takeover
    - New account fraud
    - Identity theft indicators
    """
    try:
        result = orchestrator.analyze_user_profile(
            profile_data=request.model_dump(),
            auto_investigate=auto_investigate,
        )
        return _convert_result_to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== E-commerce Order Analysis ==============


@router.post(
    "/analyze/ecommerce-order",
    response_model=FraudAnalysisResponse,
    tags=["Analysis"],
    summary="Analyze an e-commerce order for fraud",
)
async def analyze_ecommerce_order(
    request: EcommerceOrderRequest,
    auto_investigate: bool = True,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Analyze an e-commerce order for potential fraud.

    This endpoint uses the E-commerce Fraud Agent to detect:
    - Reseller fraud
    - Stolen card usage
    - Friendly fraud
    - Address mismatches
    - High-risk items
    """
    try:
        result = orchestrator.analyze_ecommerce_order(
            order_data=request.model_dump(),
            auto_investigate=auto_investigate,
        )
        return _convert_result_to_response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Comprehensive Analysis ==============


@router.post(
    "/analyze/comprehensive",
    response_model=FraudAnalysisResponse,
    tags=["Analysis"],
    summary="Perform comprehensive multi-source fraud analysis",
)
async def analyze_comprehensive(
    request: ComprehensiveRequest,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Perform comprehensive fraud analysis combining multiple data sources.

    This is useful when you have related data (e.g., a transaction
    and the user profile of the person making it). The system will
    run multiple agents and aggregate their findings.
    """
    try:
        transaction_data = request.transaction.model_dump() if request.transaction else None
        user_profile = request.user_profile.model_dump() if request.user_profile else None
        order_data = request.order.model_dump() if request.order else None

        if not any([transaction_data, user_profile, order_data]):
            raise HTTPException(
                status_code=400,
                detail="At least one data source (transaction, user_profile, or order) must be provided",
            )

        result = orchestrator.analyze_comprehensive(
            transaction_data=transaction_data,
            user_profile=user_profile,
            order_data=order_data,
            auto_investigate=request.auto_investigate,
        )
        return _convert_result_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Batch Analysis ==============


@router.post(
    "/analyze/batch",
    response_model=BatchAnalysisResponse,
    tags=["Analysis"],
    summary="Analyze multiple items in batch",
)
async def analyze_batch(
    request: BatchAnalysisRequest,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings),
):
    """
    Analyze multiple items in batch.

    Returns results sorted by risk score (highest first) along with
    summary statistics including risk distribution.
    """
    try:
        # Map API enum to internal enum
        entity_type_map = {
            EntityTypeEnum.TRANSACTION: EntityType.TRANSACTION,
            EntityTypeEnum.INSURANCE_CLAIM: EntityType.INSURANCE_CLAIM,
            EntityTypeEnum.USER_PROFILE: EntityType.USER_PROFILE,
            EntityTypeEnum.ECOMMERCE_ORDER: EntityType.ECOMMERCE_ORDER,
        }

        results = orchestrator.batch_analyze(
            items=request.items,
            entity_type=entity_type_map[request.entity_type],
            auto_investigate=request.auto_investigate,
        )

        summary = orchestrator.get_high_risk_summary(
            results=results,
            threshold=settings.high_risk_threshold,
        )

        return BatchAnalysisResponse(
            results=[_convert_result_to_response(r) for r in results],
            summary=summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Fraud Simulation Endpoint ==============

from orchestrator import FraudDetectionOrchestrator


@router.get(
    "/simulate-attack",
    tags=["Simulation"],
    summary="Simulate a fraud attack and analyze system response",
)
async def simulate_attack(
    attack_type: str = None,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Simulate a fraud attack (red team) and return both the attack payload and the system's analysis.
    """
    try:
        result = orchestrator.simulate_fraud_attack(attack_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Detection Score Dashboard Endpoint ==============


@router.post(
    "/detection-score",
    response_model=DetectionScoreResponse,
    tags=["Simulation"],
    summary="Run detection score analysis across attack types",
)
async def run_detection_score_analysis(
    request: DetectionScoreRequest,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Run batch simulations across multiple attack types and compute detection metrics.

    Returns:
    - Detection rate per attack type (% of attacks caught)
    - False negative rate per attack type (% that slipped through)
    - Average confidence score per attack type
    - Overall aggregated metrics
    """
    try:
        result = orchestrator.run_detection_score_analysis(
            attack_types=request.attack_types,
            simulations_per_type=request.simulations_per_type,
            detection_threshold=request.detection_threshold,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/detection-score",
    response_model=DetectionScoreResponse,
    tags=["Simulation"],
    summary="Run detection score analysis with default parameters",
)
async def run_detection_score_analysis_get(
    simulations_per_type: int = 1,
    detection_threshold: float = None,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Run batch simulations across all attack types with default parameters.
    Use the POST endpoint for more control over which attack types to test.
    """
    try:
        result = orchestrator.run_detection_score_analysis(
            attack_types=None,
            simulations_per_type=simulations_per_type,
            detection_threshold=detection_threshold,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Mixed Detection Score Endpoint ==============


@router.post(
    "/detection-score-mixed",
    response_model=MixedDetectionResponse,
    tags=["Simulation"],
    summary="Run detection analysis with mixed legitimate and fraudulent transactions",
)
async def run_mixed_detection_analysis(
    request: MixedDetectionRequest,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Run detection analysis with a mix of legitimate AND fraudulent transactions.

    This provides proper evaluation metrics including:
    - **Confusion Matrix**: TP, TN, FP, FN counts
    - **Precision**: Of all flagged as fraud, how many were actually fraud?
    - **Recall**: Of all actual fraud, how many did we catch?
    - **F1 Score**: Balanced measure of precision and recall
    - **False Positive Rate**: What % of legitimate transactions were incorrectly flagged?
    - **False Negative Rate**: What % of fraud transactions slipped through?

    Use this endpoint to evaluate real-world applicability of the fraud detection system.
    """
    try:
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=request.num_legitimate,
            num_fraudulent=request.num_fraudulent,
            detection_threshold=request.detection_threshold,
            use_llm=request.use_llm,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/detection-score-mixed",
    response_model=MixedDetectionResponse,
    tags=["Simulation"],
    summary="Run mixed detection analysis with default parameters",
)
async def run_mixed_detection_analysis_get(
    num_legitimate: int = 10,
    num_fraudulent: int = 10,
    detection_threshold: float = None,
    orchestrator: FraudDetectionOrchestrator = Depends(get_orchestrator),
):
    """
    Run mixed detection analysis with default parameters.

    Quick way to test the system's ability to distinguish legitimate from fraudulent transactions.
    Use the POST endpoint for more control over parameters.
    """
    try:
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=num_legitimate,
            num_fraudulent=num_fraudulent,
            detection_threshold=detection_threshold,
            use_llm=False,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
