"""
Feedback Loop System for Fraud Detection.

This module implements a complete feedback loop that:
1. Collects outcomes (chargebacks, confirmations, false positives)
2. Updates model training data
3. Triggers model retraining when needed
4. Adjusts rule thresholds dynamically

ARCHITECTURE:
=============

    ┌──────────────────────────────────────────────────────────────────┐
    │                      FEEDBACK LOOP FLOW                          │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   Prediction ──► Decision ──► Outcome ──► Feedback ──► Learning │
    │       │             │            │            │            │     │
    │       ▼             ▼            ▼            ▼            ▼     │
    │   ┌───────┐    ┌────────┐   ┌────────┐  ┌─────────┐  ┌────────┐ │
    │   │ Store │    │ Action │   │Chargeback│ │ Update  │  │Retrain │ │
    │   │ Pred. │    │ Taken  │   │Confirm  │  │ Labels  │  │ Model  │ │
    │   └───────┘    └────────┘   │Override │  └─────────┘  └────────┘ │
    │                             └────────┘                           │
    └──────────────────────────────────────────────────────────────────┘


FEEDBACK SOURCES:
=================

1. **Chargebacks**: Customer disputed the charge → Confirmed fraud
2. **Fraud Reports**: User reports unauthorized transaction → Confirmed fraud
3. **Manual Review**: Analyst confirms or dismisses alert → Ground truth
4. **Time Decay**: No dispute after 90 days → Likely legitimate

USAGE:
======

    from ml.feedback import FeedbackCollector, get_feedback_collector

    # Record outcome
    collector = get_feedback_collector()
    collector.record_outcome(
        prediction_id="pred_123",
        outcome="chargeback",
        outcome_details={"amount": 500.0, "reason": "unauthorized"},
    )

    # Check if retraining needed
    if collector.should_retrain():
        collector.trigger_retraining()

"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional
from enum import Enum
import logging
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class OutcomeType(Enum):
    """Types of feedback outcomes."""

    CHARGEBACK = "chargeback"  # Customer disputed → fraud
    FRAUD_REPORT = "fraud_report"  # User reported fraud
    ANALYST_CONFIRMED = "analyst_confirmed"  # Analyst confirmed fraud
    ANALYST_DISMISSED = "analyst_dismissed"  # Analyst dismissed as false positive
    CUSTOMER_CONFIRMED = "customer_confirmed"  # Customer confirmed legitimate
    TIME_DECAY = "time_decay"  # No dispute after threshold → legitimate
    UNKNOWN = "unknown"


@dataclass
class PredictionRecord:
    """Record of a model prediction for feedback tracking."""

    prediction_id: str
    transaction_id: str
    model_name: str
    model_version: str

    # Prediction details
    risk_score: float
    confidence: float
    decision: str  # allow, block, review
    features: dict[str, Any]

    # Timestamps
    predicted_at: datetime

    # Outcome (filled in later)
    outcome: Optional[OutcomeType] = None
    outcome_at: Optional[datetime] = None
    outcome_details: dict[str, Any] = field(default_factory=dict)

    # Computed fields
    is_labeled: bool = False
    was_correct: Optional[bool] = None  # True if prediction matched outcome


@dataclass
class FeedbackStats:
    """Statistics about feedback collection."""

    total_predictions: int = 0
    labeled_predictions: int = 0

    # Outcome breakdown
    chargebacks: int = 0
    fraud_reports: int = 0
    analyst_confirmed: int = 0
    analyst_dismissed: int = 0
    time_decay: int = 0

    # Model performance (on labeled data)
    true_positives: int = 0  # Predicted fraud, was fraud
    false_positives: int = 0  # Predicted fraud, was legitimate
    true_negatives: int = 0  # Predicted legitimate, was legitimate
    false_negatives: int = 0  # Predicted legitimate, was fraud

    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)"""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)"""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """F1 Score: 2 * (precision * recall) / (precision + recall)"""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        """FPR: FP / (FP + TN)"""
        denom = self.false_positives + self.true_negatives
        return self.false_positives / denom if denom > 0 else 0.0


class FeedbackCollector:
    """
    Collects and processes feedback for model improvement.

    This is the core component that connects outcomes to model updates.
    """

    def __init__(
        self,
        time_decay_days: int = 90,
        retraining_threshold: int = 1000,
        performance_alert_threshold: float = 0.7,
    ):
        """
        Initialize feedback collector.

        Args:
            time_decay_days: Days after which unlabeled txn is assumed legitimate
            retraining_threshold: Number of new labels before suggesting retraining
            performance_alert_threshold: F1 score below which to alert
        """
        self.time_decay_days = time_decay_days
        self.retraining_threshold = retraining_threshold
        self.performance_alert_threshold = performance_alert_threshold

        # Storage (in production, use database)
        self._predictions: dict[str, PredictionRecord] = {}
        self._labels_since_retrain: int = 0
        self._stats = FeedbackStats()

        # Threshold adjustment tracking
        self._threshold_adjustments: list[dict] = []

    def record_prediction(
        self,
        prediction_id: str,
        transaction_id: str,
        model_name: str,
        model_version: str,
        risk_score: float,
        confidence: float,
        decision: str,
        features: dict[str, Any],
    ):
        """
        Record a prediction for later feedback matching.

        This should be called every time a prediction is made.
        """
        record = PredictionRecord(
            prediction_id=prediction_id,
            transaction_id=transaction_id,
            model_name=model_name,
            model_version=model_version,
            risk_score=risk_score,
            confidence=confidence,
            decision=decision,
            features=features,
            predicted_at=datetime.utcnow(),
        )

        self._predictions[prediction_id] = record
        self._stats.total_predictions += 1

        logger.debug(f"Recorded prediction {prediction_id} for transaction {transaction_id}")

    def record_outcome(
        self,
        prediction_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        outcome: str = "unknown",
        outcome_details: Optional[dict] = None,
    ):
        """
        Record an outcome for a previous prediction.

        Args:
            prediction_id: ID of the prediction (preferred)
            transaction_id: Transaction ID (fallback lookup)
            outcome: Outcome type (chargeback, fraud_report, etc.)
            outcome_details: Additional details about the outcome
        """
        # Find the prediction record
        record = None
        if prediction_id and prediction_id in self._predictions:
            record = self._predictions[prediction_id]
        elif transaction_id:
            # Search by transaction ID
            for pred in self._predictions.values():
                if pred.transaction_id == transaction_id:
                    record = pred
                    break

        if not record:
            logger.warning(f"No prediction found for outcome: {prediction_id or transaction_id}")
            return

        # Update the record
        try:
            record.outcome = OutcomeType(outcome)
        except ValueError:
            record.outcome = OutcomeType.UNKNOWN

        record.outcome_at = datetime.utcnow()
        record.outcome_details = outcome_details or {}
        record.is_labeled = True

        # Determine if prediction was correct
        is_fraud = record.outcome in [
            OutcomeType.CHARGEBACK,
            OutcomeType.FRAUD_REPORT,
            OutcomeType.ANALYST_CONFIRMED,
        ]
        predicted_fraud = record.decision == "block" or record.risk_score >= 60

        record.was_correct = is_fraud == predicted_fraud

        # Update stats
        self._update_stats(record, is_fraud, predicted_fraud)
        self._labels_since_retrain += 1

        logger.info(
            f"Recorded outcome for {record.prediction_id}: "
            f"{record.outcome.value}, correct={record.was_correct}"
        )

        # Check if we should alert on performance
        self._check_performance_alert()

    def _update_stats(self, record: PredictionRecord, is_fraud: bool, predicted_fraud: bool):
        """Update statistics based on outcome."""
        self._stats.labeled_predictions += 1

        # Update outcome counts
        if record.outcome == OutcomeType.CHARGEBACK:
            self._stats.chargebacks += 1
        elif record.outcome == OutcomeType.FRAUD_REPORT:
            self._stats.fraud_reports += 1
        elif record.outcome == OutcomeType.ANALYST_CONFIRMED:
            self._stats.analyst_confirmed += 1
        elif record.outcome == OutcomeType.ANALYST_DISMISSED:
            self._stats.analyst_dismissed += 1
        elif record.outcome == OutcomeType.TIME_DECAY:
            self._stats.time_decay += 1

        # Update confusion matrix
        if predicted_fraud and is_fraud:
            self._stats.true_positives += 1
        elif predicted_fraud and not is_fraud:
            self._stats.false_positives += 1
        elif not predicted_fraud and not is_fraud:
            self._stats.true_negatives += 1
        else:  # not predicted_fraud and is_fraud
            self._stats.false_negatives += 1

    def _check_performance_alert(self):
        """Check if model performance has degraded."""
        if self._stats.labeled_predictions < 100:
            return  # Not enough data

        if self._stats.f1_score < self.performance_alert_threshold:
            logger.warning(
                f"Model performance degraded! F1={self._stats.f1_score:.3f} "
                f"(threshold={self.performance_alert_threshold})"
            )

    def should_retrain(self) -> bool:
        """Check if model should be retrained based on new labels."""
        return self._labels_since_retrain >= self.retraining_threshold

    def get_training_data(self) -> list[dict]:
        """
        Get labeled data for model retraining.

        Returns list of feature/label pairs suitable for training.
        """
        training_data = []

        for record in self._predictions.values():
            if not record.is_labeled:
                continue

            is_fraud = record.outcome in [
                OutcomeType.CHARGEBACK,
                OutcomeType.FRAUD_REPORT,
                OutcomeType.ANALYST_CONFIRMED,
            ]

            training_data.append(
                {
                    "features": record.features,
                    "label": 1 if is_fraud else 0,
                    "transaction_id": record.transaction_id,
                    "outcome": record.outcome.value,
                }
            )

        return training_data

    def trigger_retraining(self) -> dict:
        """
        Trigger model retraining.

        In production, this would:
        1. Export training data
        2. Start training pipeline (MLflow, SageMaker, etc.)
        3. Evaluate new model
        4. Deploy if performance improves

        Returns:
            Status of the retraining request
        """
        training_data = self.get_training_data()

        logger.info(f"Triggering model retraining with {len(training_data)} labeled samples")

        # Reset counter
        self._labels_since_retrain = 0

        # In production, you would:
        # 1. Save training data to feature store
        # 2. Trigger training pipeline
        # 3. Return job ID for tracking

        return {
            "status": "triggered",
            "samples": len(training_data),
            "stats": {
                "precision": self._stats.precision,
                "recall": self._stats.recall,
                "f1_score": self._stats.f1_score,
            },
        }

    def get_stats(self) -> FeedbackStats:
        """Get current feedback statistics."""
        return self._stats

    def suggest_threshold_adjustment(self) -> Optional[dict]:
        """
        Suggest threshold adjustments based on feedback.

        Returns adjustment suggestions if false positive rate is too high
        or recall is too low.
        """
        if self._stats.labeled_predictions < 100:
            return None

        suggestions = []

        # High false positive rate → raise threshold
        if self._stats.false_positive_rate > 0.3:
            suggestions.append(
                {
                    "type": "raise_threshold",
                    "reason": f"False positive rate is {self._stats.false_positive_rate:.1%}",
                    "current_impact": f"{self._stats.false_positives} false positives",
                }
            )

        # Low recall → lower threshold for certain patterns
        if self._stats.recall < 0.8 and self._stats.false_negatives > 10:
            suggestions.append(
                {
                    "type": "lower_threshold",
                    "reason": f"Recall is only {self._stats.recall:.1%}",
                    "current_impact": f"{self._stats.false_negatives} missed frauds",
                }
            )

        return (
            {
                "suggestions": suggestions,
                "current_performance": {
                    "precision": self._stats.precision,
                    "recall": self._stats.recall,
                    "f1": self._stats.f1_score,
                    "fpr": self._stats.false_positive_rate,
                },
            }
            if suggestions
            else None
        )

    def apply_time_decay(self):
        """
        Apply time decay to old unlabeled predictions.

        Transactions without dispute after threshold days are
        assumed to be legitimate.
        """
        cutoff = datetime.utcnow() - timedelta(days=self.time_decay_days)

        decayed = 0
        for record in self._predictions.values():
            if record.is_labeled:
                continue

            if record.predicted_at < cutoff:
                record.outcome = OutcomeType.TIME_DECAY
                record.outcome_at = datetime.utcnow()
                record.is_labeled = True

                # Assumed legitimate
                predicted_fraud = record.decision == "block" or record.risk_score >= 60
                record.was_correct = not predicted_fraud

                self._update_stats(record, is_fraud=False, predicted_fraud=predicted_fraud)
                decayed += 1

        if decayed > 0:
            logger.info(f"Applied time decay to {decayed} predictions")

        return decayed


# Global feedback collector
_collector: Optional[FeedbackCollector] = None


def get_feedback_collector() -> FeedbackCollector:
    """Get the global feedback collector instance."""
    global _collector
    if _collector is None:
        _collector = FeedbackCollector()
    return _collector
