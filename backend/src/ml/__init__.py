"""
Machine Learning module for fraud detection.
"""

from ml.models import (
    FraudModel,
    RuleBasedModel,
    ModelRegistry,
    ModelPrediction,
    FeatureSet,
    ModelType,
    get_model_registry,
    get_fraud_model,
)

from ml.feedback import (
    FeedbackCollector,
    FeedbackStats,
    OutcomeType,
    PredictionRecord,
    get_feedback_collector,
)

__all__ = [
    # Models
    "FraudModel",
    "RuleBasedModel",
    "ModelRegistry",
    "ModelPrediction",
    "FeatureSet",
    "ModelType",
    "get_model_registry",
    "get_fraud_model",
    # Feedback
    "FeedbackCollector",
    "FeedbackStats",
    "OutcomeType",
    "PredictionRecord",
    "get_feedback_collector",
]
