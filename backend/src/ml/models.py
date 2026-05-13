"""
Machine Learning Model Interface for Fraud Detection.

This module provides a standardized interface for integrating ML models
into the fraud detection pipeline. It supports:

1. Multiple model backends (scikit-learn, XGBoost, PyTorch, etc.)
2. Feature extraction and preprocessing
3. Model versioning and A/B testing
4. Explanation generation (SHAP, LIME)
5. Online learning / model updates

ARCHITECTURE:
=============

    Transaction ──► FeatureExtractor ──► MLModel ──► PostProcessor ──► Risk Score
                          │                  │              │
                          ▼                  ▼              ▼
                    Feature Store      Model Registry   Explanations


USAGE:
======

    from ml.models import get_fraud_model

    model = get_fraud_model("transaction_fraud_v2")

    result = model.predict(
        features=extracted_features,
        return_explanation=True,
    )

    print(result.risk_score)      # 0-100
    print(result.confidence)      # 0-1
    print(result.explanation)     # Feature importances

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of ML models supported."""

    RULE_BASED = "rule_based"  # Current heuristic rules
    GRADIENT_BOOSTING = "gradient_boosting"  # XGBoost, LightGBM, CatBoost
    NEURAL_NETWORK = "neural_network"  # Deep learning models
    ENSEMBLE = "ensemble"  # Combination of multiple models
    ANOMALY_DETECTION = "anomaly_detection"  # Isolation Forest, Autoencoders


@dataclass
class ModelPrediction:
    """Result from a model prediction."""

    risk_score: float  # 0-100 scale
    confidence: float  # 0-1 scale (how confident the model is)
    fraud_probability: float  # 0-1 raw probability

    # Explanation of the prediction
    top_features: list[dict[str, Any]] = field(default_factory=list)
    explanation_text: Optional[str] = None

    # Model metadata
    model_name: str = ""
    model_version: str = ""

    # For A/B testing
    experiment_id: Optional[str] = None
    variant: Optional[str] = None


@dataclass
class FeatureSet:
    """Extracted features for model input."""

    # Transaction features
    amount: float = 0.0
    amount_zscore: float = 0.0  # How many std devs from user's average
    is_round_amount: bool = False

    # Velocity features
    transactions_1h: int = 0
    transactions_24h: int = 0
    amount_1h: float = 0.0
    amount_24h: float = 0.0
    unique_merchants_24h: int = 0

    # Temporal features
    hour_of_day: int = 0
    day_of_week: int = 0
    is_weekend: bool = False
    is_night: bool = False  # 12am - 6am

    # Geographic features
    is_high_risk_country: bool = False
    distance_from_last_txn_km: float = 0.0
    is_impossible_travel: bool = False

    # Device/Network features
    is_new_device: bool = False
    is_vpn: bool = False
    is_tor: bool = False
    is_datacenter_ip: bool = False
    device_age_days: int = 0

    # User behavior features
    account_age_days: int = 0
    avg_transaction_amount: float = 0.0
    transaction_frequency: float = 0.0  # per day

    # Merchant features
    is_high_risk_merchant: bool = False
    merchant_category_risk: float = 0.0

    # Additional raw features for model input
    raw_features: dict[str, Any] = field(default_factory=dict)


class FraudModel(ABC):
    """
    Abstract base class for fraud detection models.

    All models must implement this interface to be used in the
    fraud detection pipeline.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Model name/identifier."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Model version."""
        pass

    @property
    @abstractmethod
    def model_type(self) -> ModelType:
        """Type of model."""
        pass

    @abstractmethod
    def predict(
        self,
        features: FeatureSet,
        return_explanation: bool = False,
    ) -> ModelPrediction:
        """
        Make a fraud prediction.

        Args:
            features: Extracted features for the transaction
            return_explanation: Whether to include feature explanations

        Returns:
            ModelPrediction with risk score and metadata
        """
        pass

    @abstractmethod
    def extract_features(self, transaction_data: dict[str, Any]) -> FeatureSet:
        """
        Extract features from raw transaction data.

        Args:
            transaction_data: Raw transaction dictionary

        Returns:
            FeatureSet ready for model input
        """
        pass

    def predict_from_raw(
        self,
        transaction_data: dict[str, Any],
        return_explanation: bool = False,
    ) -> ModelPrediction:
        """
        Convenience method to predict from raw transaction data.
        """
        features = self.extract_features(transaction_data)
        return self.predict(features, return_explanation)


class RuleBasedModel(FraudModel):
    """
    Current rule-based model (wraps existing agent logic).

    This serves as:
    1. Baseline model to compare ML models against
    2. Fallback when ML models are unavailable
    3. Override layer for compliance rules that must always apply
    """

    def __init__(self):
        self._name = "rule_based_v1"
        self._version = "1.0.0"

        # Risk weights for different signals
        self.weights = {
            "high_amount": 20,
            "velocity": 25,
            "high_risk_location": 15,
            "impossible_travel": 30,
            "new_device": 10,
            "vpn_tor": 15,
            "night_transaction": 5,
            "high_risk_merchant": 10,
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def model_type(self) -> ModelType:
        return ModelType.RULE_BASED

    def extract_features(self, transaction_data: dict[str, Any]) -> FeatureSet:
        """Extract features from transaction data."""
        features = FeatureSet()

        features.amount = transaction_data.get("amount", 0.0)
        features.hour_of_day = 12  # Would parse from timestamp
        features.is_night = features.hour_of_day < 6 or features.hour_of_day >= 22

        # Store raw data for rule evaluation
        features.raw_features = transaction_data

        return features

    def predict(
        self,
        features: FeatureSet,
        return_explanation: bool = False,
    ) -> ModelPrediction:
        """Apply rules to calculate risk score."""
        score = 0.0
        signals = []

        # Amount rules
        if features.amount > 5000:
            score += self.weights["high_amount"]
            signals.append({"feature": "amount", "contribution": self.weights["high_amount"]})

        # Velocity rules
        if features.transactions_1h > 5:
            score += self.weights["velocity"]
            signals.append({"feature": "velocity_1h", "contribution": self.weights["velocity"]})

        # Geographic rules
        if features.is_high_risk_country:
            score += self.weights["high_risk_location"]
            signals.append(
                {"feature": "high_risk_country", "contribution": self.weights["high_risk_location"]}
            )

        if features.is_impossible_travel:
            score += self.weights["impossible_travel"]
            signals.append(
                {"feature": "impossible_travel", "contribution": self.weights["impossible_travel"]}
            )

        # Device rules
        if features.is_new_device:
            score += self.weights["new_device"]
            signals.append({"feature": "new_device", "contribution": self.weights["new_device"]})

        if features.is_vpn or features.is_tor:
            score += self.weights["vpn_tor"]
            signals.append({"feature": "vpn_tor", "contribution": self.weights["vpn_tor"]})

        # Time rules
        if features.is_night:
            score += self.weights["night_transaction"]
            signals.append(
                {"feature": "night_time", "contribution": self.weights["night_transaction"]}
            )

        # Merchant rules
        if features.is_high_risk_merchant:
            score += self.weights["high_risk_merchant"]
            signals.append(
                {
                    "feature": "high_risk_merchant",
                    "contribution": self.weights["high_risk_merchant"],
                }
            )

        # Cap at 100
        score = min(score, 100.0)

        # Confidence based on how many rules triggered
        confidence = min(len(signals) / 5, 1.0) if signals else 0.3

        return ModelPrediction(
            risk_score=score,
            confidence=confidence,
            fraud_probability=score / 100.0,
            top_features=signals if return_explanation else [],
            model_name=self.name,
            model_version=self.version,
        )


class ModelRegistry:
    """
    Registry for managing multiple model versions.

    Supports:
    - Model versioning
    - A/B testing between models
    - Gradual rollout of new models
    - Fallback to previous versions
    """

    def __init__(self):
        self._models: dict[str, FraudModel] = {}
        self._default_model: Optional[str] = None
        self._ab_tests: dict[str, dict] = {}  # experiment_id -> config

        # Register default rule-based model
        self.register(RuleBasedModel())
        self._default_model = "rule_based_v1"

    def register(self, model: FraudModel):
        """Register a model."""
        key = f"{model.name}"
        self._models[key] = model
        logger.info(f"Registered model: {key} (v{model.version})")

    def get(self, name: str) -> Optional[FraudModel]:
        """Get a model by name."""
        return self._models.get(name)

    def get_default(self) -> FraudModel:
        """Get the default model."""
        if self._default_model and self._default_model in self._models:
            return self._models[self._default_model]
        # Fallback to rule-based
        return RuleBasedModel()

    def set_default(self, name: str):
        """Set the default model."""
        if name in self._models:
            self._default_model = name
            logger.info(f"Default model set to: {name}")

    def list_models(self) -> list[dict[str, str]]:
        """List all registered models."""
        return [
            {
                "name": model.name,
                "version": model.version,
                "type": model.model_type.value,
                "is_default": model.name == self._default_model,
            }
            for model in self._models.values()
        ]


# Global model registry
_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry."""
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


def get_fraud_model(name: Optional[str] = None) -> FraudModel:
    """
    Get a fraud detection model.

    Args:
        name: Model name, or None for default

    Returns:
        FraudModel instance
    """
    registry = get_model_registry()
    if name:
        model = registry.get(name)
        if model:
            return model
        logger.warning(f"Model '{name}' not found, using default")
    return registry.get_default()
