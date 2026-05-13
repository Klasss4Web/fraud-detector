"""
Pydantic models for the Fraud Detection API.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class RiskLevelEnum(str, Enum):
    """Risk classification levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntityTypeEnum(str, Enum):
    """Supported entity types for fraud detection"""

    TRANSACTION = "transaction"
    INSURANCE_CLAIM = "claim"
    USER_PROFILE = "profile"
    ECOMMERCE_ORDER = "order"


# ============== Request Models ==============


class TransactionRequest(BaseModel):
    """Transaction data for fraud analysis"""

    transaction_id: str = Field(..., description="Unique transaction identifier")
    amount: float = Field(..., ge=0, description="Transaction amount")
    currency: str = Field(default="USD", description="Currency code")
    merchant_category: str = Field(..., description="Merchant category code")
    merchant_name: str = Field(..., description="Merchant name")
    location: str = Field(..., description="Transaction location")
    device_id: Optional[str] = Field(None, description="Device identifier")
    ip_address: Optional[str] = Field(None, description="IP address")
    timestamp: Optional[str] = Field(None, description="Transaction timestamp")
    user_id: Optional[str] = Field(None, description="Associated user ID")

    model_config = {"extra": "allow"}


class InsuranceClaimRequest(BaseModel):
    """Insurance claim data for fraud analysis"""

    claim_id: str = Field(..., description="Unique claim identifier")
    claim_amount: float = Field(..., ge=0, description="Claim amount")
    claim_type: str = Field(..., description="Type of claim (auto, health, property, etc.)")
    incident_date: str = Field(..., description="Date of incident")
    filing_date: str = Field(..., description="Date claim was filed")
    description: str = Field(..., description="Claim description")
    claimant_id: str = Field(..., description="Claimant identifier")
    policy_id: Optional[str] = Field(None, description="Policy identifier")
    witnesses: Optional[list[str]] = Field(default=[], description="List of witnesses")

    model_config = {"extra": "allow"}


class UserProfileRequest(BaseModel):
    """User profile data for identity fraud analysis"""

    user_id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    phone: Optional[str] = Field(None, description="Phone number")
    account_age_days: int = Field(..., ge=0, description="Account age in days")
    device_count: int = Field(default=1, ge=1, description="Number of devices")
    login_frequency: float = Field(default=1.0, description="Login frequency")
    failed_login_attempts: int = Field(default=0, ge=0, description="Failed login attempts")
    location_changes: int = Field(default=0, ge=0, description="Recent location changes")

    model_config = {"extra": "allow"}


class EcommerceOrderRequest(BaseModel):
    """E-commerce order data for fraud analysis"""

    order_id: str = Field(..., description="Unique order identifier")
    order_total: float = Field(..., ge=0, description="Order total amount")
    item_count: int = Field(..., ge=1, description="Number of items")
    shipping_address: str = Field(..., description="Shipping address")
    billing_address: str = Field(..., description="Billing address")
    customer_id: str = Field(..., description="Customer identifier")
    payment_method: str = Field(..., description="Payment method")
    items: Optional[list[dict[str, Any]]] = Field(default=[], description="Order items")
    is_expedited: bool = Field(default=False, description="Expedited shipping requested")

    model_config = {"extra": "allow"}


class ComprehensiveRequest(BaseModel):
    """Combined data for comprehensive fraud analysis"""

    transaction: Optional[TransactionRequest] = Field(None, description="Transaction data")
    user_profile: Optional[UserProfileRequest] = Field(None, description="User profile data")
    order: Optional[EcommerceOrderRequest] = Field(None, description="E-commerce order data")
    auto_investigate: bool = Field(default=True, description="Auto-investigate high-risk cases")


class BatchAnalysisRequest(BaseModel):
    """Batch analysis request"""

    items: list[dict[str, Any]] = Field(..., description="List of items to analyze")
    entity_type: EntityTypeEnum = Field(..., description="Type of entities being analyzed")
    auto_investigate: bool = Field(default=False, description="Auto-investigate high-risk cases")


# ============== Response Models ==============


class FraudSignalResponse(BaseModel):
    """Individual fraud signal"""

    name: str = Field(..., description="Signal name")
    description: str = Field(..., description="Signal description")
    weight: float = Field(..., ge=0, le=1, description="Signal weight (0-1)")
    category: str = Field(..., description="Signal category")


class FraudAnalysisResponse(BaseModel):
    """Complete fraud analysis result"""

    entity_id: str = Field(..., description="Entity identifier")
    entity_type: str = Field(..., description="Entity type")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100)")
    risk_level: RiskLevelEnum = Field(..., description="Risk level classification")
    requires_action: bool = Field(..., description="Whether action is required")
    recommendation: str = Field(..., description="Recommended action")
    signals: list[FraudSignalResponse] = Field(default=[], description="Detected fraud signals")
    agent_results: dict[str, float] = Field(default={}, description="Individual agent scores")
    investigation_report: Optional[dict[str, Any]] = Field(
        None, description="Investigation report if available"
    )


class BatchAnalysisResponse(BaseModel):
    """Batch analysis response"""

    results: list[FraudAnalysisResponse] = Field(..., description="Analysis results")
    summary: dict[str, Any] = Field(..., description="Summary statistics")


class DependencyHealth(BaseModel):
    """Health status of a dependency."""

    status: str = Field(..., description="Health status: healthy, unhealthy, unavailable")
    latency_ms: Optional[float] = Field(None, description="Response latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """API health check response"""

    status: str = Field(..., description="Overall service status: healthy, degraded, unhealthy")
    version: str = Field(..., description="API version")
    agents_loaded: list[str] = Field(..., description="Loaded agents")
    dependencies: Optional[dict[str, DependencyHealth]] = Field(
        None, description="Health status of dependencies (database, cache, etc.)"
    )
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")


class ErrorResponse(BaseModel):
    """Error response"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional details")


# ============== Detection Score Models ==============


class DetectionScoreRequest(BaseModel):
    """Request model for detection score analysis"""

    attack_types: Optional[list[str]] = Field(
        None,
        description="List of attack types to test. If not provided, all types are tested.",
    )
    simulations_per_type: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of simulations to run per attack type (1-10)",
    )
    detection_threshold: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Risk score threshold to consider attack caught. Defaults to system threshold.",
    )


class TransactionResultDetail(BaseModel):
    """Individual transaction result in detection score analysis"""

    transaction_id: str = Field(..., description="Transaction identifier")
    risk_score: float = Field(..., description="Risk score assigned")
    risk_level: str = Field(..., description="Risk level classification")
    was_caught: bool = Field(..., description="Whether the attack was detected")
    requires_action: bool = Field(..., description="Whether action was flagged")


class SimulationDetail(BaseModel):
    """Details of a single simulation run"""

    simulation_number: int = Field(..., description="Simulation number")
    description: str = Field(..., description="Attack description")
    transactions: list[TransactionResultDetail] = Field(..., description="Transaction results")


class AttackTypeMetrics(BaseModel):
    """Metrics for a specific attack type"""

    attack_type: str = Field(..., description="Attack type name")
    total_transactions: int = Field(..., description="Total transactions analyzed")
    caught_count: int = Field(..., description="Number of attacks caught")
    missed_count: int = Field(..., description="Number of attacks missed")
    detection_rate: float = Field(..., description="Percentage of attacks caught")
    false_negative_rate: float = Field(
        ..., description="Percentage of attacks that slipped through"
    )
    average_confidence_score: float = Field(
        ..., description="Average risk score for this attack type"
    )
    simulations: list[SimulationDetail] = Field(..., description="Detailed simulation results")


class OverallMetrics(BaseModel):
    """Overall detection metrics across all attack types"""

    total_attack_types_tested: int = Field(..., description="Number of attack types tested")
    total_simulations_run: int = Field(..., description="Total simulations executed")
    total_transactions_analyzed: int = Field(..., description="Total transactions analyzed")
    total_attacks_caught: int = Field(..., description="Total attacks detected")
    total_attacks_missed: int = Field(..., description="Total attacks missed")
    overall_detection_rate: float = Field(..., description="Overall percentage of attacks caught")
    overall_false_negative_rate: float = Field(
        ..., description="Overall percentage of attacks missed"
    )
    overall_average_confidence: float = Field(
        ..., description="Average confidence score across all tests"
    )
    detection_threshold_used: float = Field(
        ..., description="Risk score threshold used for detection"
    )


class DetectionScoreResponse(BaseModel):
    """Complete detection score analysis response"""

    metrics_by_attack_type: dict[str, AttackTypeMetrics] = Field(
        ..., description="Metrics broken down by attack type"
    )
    overall_metrics: OverallMetrics = Field(
        ..., description="Aggregated metrics across all attack types"
    )


# ============== Mixed Detection Score Models ==============


class MixedDetectionRequest(BaseModel):
    """Request model for mixed detection analysis (legitimate + fraudulent)"""

    num_legitimate: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of legitimate transactions to generate (1-50)",
    )
    num_fraudulent: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of fraudulent transactions to generate (1-50)",
    )
    detection_threshold: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Risk score threshold for fraud detection. Defaults to system threshold.",
    )
    use_llm: bool = Field(
        default=False,
        description="Use LLM for transaction generation (True) or deterministic generation (False)",
    )


class ConfusionMatrixResponse(BaseModel):
    """Confusion matrix for binary classification"""

    true_positives: int = Field(..., description="Fraud correctly detected")
    true_negatives: int = Field(..., description="Legitimate correctly allowed")
    false_positives: int = Field(..., description="Legitimate incorrectly flagged as fraud")
    false_negatives: int = Field(..., description="Fraud incorrectly missed")


class MetricsResponse(BaseModel):
    """Classification metrics"""

    accuracy: float = Field(..., description="Overall accuracy (TP+TN)/Total")
    precision: float = Field(..., description="Precision: TP/(TP+FP)")
    recall: float = Field(..., description="Recall/Sensitivity: TP/(TP+FN)")
    f1_score: float = Field(..., description="F1 Score: harmonic mean of precision and recall")
    specificity: float = Field(..., description="Specificity: TN/(TN+FP)")
    false_positive_rate: float = Field(..., description="False Positive Rate: FP/(FP+TN)")
    false_negative_rate: float = Field(..., description="False Negative Rate: FN/(FN+TP)")


class SummaryResponse(BaseModel):
    """Summary statistics"""

    total_transactions: int = Field(..., description="Total transactions analyzed")
    total_legitimate: int = Field(..., description="Number of legitimate transactions")
    total_fraudulent: int = Field(..., description="Number of fraudulent transactions")
    detection_threshold: float = Field(..., description="Risk score threshold used")
    average_fraud_score: float = Field(..., description="Average risk score for fraud transactions")
    average_legitimate_score: float = Field(
        ..., description="Average risk score for legitimate transactions"
    )
    score_separation: float = Field(
        ..., description="Difference between avg fraud and legitimate scores"
    )


class InterpretationResponse(BaseModel):
    """Human-readable interpretation of metrics"""

    accuracy_meaning: str = Field(..., description="Plain English explanation of accuracy")
    precision_meaning: str = Field(..., description="Plain English explanation of precision")
    recall_meaning: str = Field(..., description="Plain English explanation of recall")
    f1_meaning: str = Field(..., description="Plain English explanation of F1 score")
    fpr_meaning: str = Field(..., description="Plain English explanation of false positive rate")
    fnr_meaning: str = Field(..., description="Plain English explanation of false negative rate")


class TransactionOutcome(BaseModel):
    """Individual transaction outcome in mixed analysis"""

    transaction_id: str = Field(..., description="Transaction identifier")
    expected_fraud: bool = Field(..., description="Whether transaction was labeled as fraud")
    predicted_fraud: bool = Field(..., description="Whether system flagged as fraud")
    risk_score: float = Field(..., description="Risk score assigned by system")
    risk_level: str = Field(..., description="Risk level classification")
    outcome: str = Field(
        ...,
        description="Classification outcome: true_positive, true_negative, false_positive, false_negative",
    )
    fraud_type: str = Field(..., description="Type of fraud (for fraudulent transactions)")
    amount: float = Field(..., description="Transaction amount")
    location: str = Field(..., description="Transaction location")
    merchant_category: str = Field(..., description="Merchant category")


class MixedDetectionResponse(BaseModel):
    """Complete mixed detection analysis response"""

    confusion_matrix: ConfusionMatrixResponse = Field(
        ..., description="Confusion matrix with TP, TN, FP, FN counts"
    )
    metrics: MetricsResponse = Field(
        ..., description="Classification metrics (accuracy, precision, recall, F1, etc.)"
    )
    summary: SummaryResponse = Field(..., description="Summary statistics")
    interpretation: InterpretationResponse = Field(
        ..., description="Human-readable interpretation of results"
    )
    detailed_results: list[TransactionOutcome] = Field(
        ..., description="Detailed outcome for each transaction"
    )
