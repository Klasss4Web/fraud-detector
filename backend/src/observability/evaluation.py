"""
Evaluation framework for fraud detection system.

Provides tools for evaluating agent performance, tracking accuracy,
and implementing feedback loops for continuous improvement.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class EvaluationOutcome(Enum):
    """Outcome of evaluating a fraud decision."""

    TRUE_POSITIVE = "true_positive"  # Correctly identified fraud
    TRUE_NEGATIVE = "true_negative"  # Correctly allowed legitimate
    FALSE_POSITIVE = "false_positive"  # Incorrectly blocked legitimate
    FALSE_NEGATIVE = "false_negative"  # Incorrectly allowed fraud


@dataclass
class EvaluationRecord:
    """Record of a single evaluation."""

    alert_id: str
    entity_type: str
    predicted_action: str
    predicted_risk_score: float
    predicted_confidence: float
    actual_outcome: Optional[EvaluationOutcome] = None
    human_decision: Optional[str] = None
    feedback_source: str = "unknown"  # human_review, chargeback, user_report
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "entity_type": self.entity_type,
            "predicted_action": self.predicted_action,
            "predicted_risk_score": self.predicted_risk_score,
            "predicted_confidence": self.predicted_confidence,
            "actual_outcome": self.actual_outcome.value if self.actual_outcome else None,
            "human_decision": self.human_decision,
            "feedback_source": self.feedback_source,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class ConfusionMatrix:
    """Confusion matrix for binary classification."""

    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def total(self) -> int:
        return (
            self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
        )

    @property
    def accuracy(self) -> float:
        """Overall accuracy."""
        if self.total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.total

    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)"""
        denominator = self.true_positives + self.false_positives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def recall(self) -> float:
        """Recall (Sensitivity): TP / (TP + FN)"""
        denominator = self.true_positives + self.false_negatives
        if denominator == 0:
            return 0.0
        return self.true_positives / denominator

    @property
    def f1_score(self) -> float:
        """F1 Score: 2 * (precision * recall) / (precision + recall)"""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def false_positive_rate(self) -> float:
        """False Positive Rate: FP / (FP + TN)"""
        denominator = self.false_positives + self.true_negatives
        if denominator == 0:
            return 0.0
        return self.false_positives / denominator

    @property
    def false_negative_rate(self) -> float:
        """False Negative Rate: FN / (FN + TP)"""
        denominator = self.false_negatives + self.true_positives
        if denominator == 0:
            return 0.0
        return self.false_negatives / denominator

    def add_outcome(self, outcome: EvaluationOutcome):
        """Add an outcome to the matrix."""
        if outcome == EvaluationOutcome.TRUE_POSITIVE:
            self.true_positives += 1
        elif outcome == EvaluationOutcome.TRUE_NEGATIVE:
            self.true_negatives += 1
        elif outcome == EvaluationOutcome.FALSE_POSITIVE:
            self.false_positives += 1
        elif outcome == EvaluationOutcome.FALSE_NEGATIVE:
            self.false_negatives += 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "confusion_matrix": {
                "true_positives": self.true_positives,
                "true_negatives": self.true_negatives,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives,
            },
            "metrics": {
                "accuracy": round(self.accuracy, 4),
                "precision": round(self.precision, 4),
                "recall": round(self.recall, 4),
                "f1_score": round(self.f1_score, 4),
                "false_positive_rate": round(self.false_positive_rate, 4),
                "false_negative_rate": round(self.false_negative_rate, 4),
            },
            "total_evaluated": self.total,
        }


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for a specific agent."""

    agent_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    min_execution_time: float = float("inf")
    max_execution_time: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions

    @property
    def avg_execution_time(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.total_execution_time / self.total_executions

    def record_execution(self, success: bool, execution_time: float):
        """Record an execution."""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        self.total_execution_time += execution_time
        self.min_execution_time = min(self.min_execution_time, execution_time)
        self.max_execution_time = max(self.max_execution_time, execution_time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "total_executions": self.total_executions,
            "success_rate": round(self.success_rate, 4),
            "avg_execution_time_ms": round(self.avg_execution_time * 1000, 2),
            "min_execution_time_ms": round(self.min_execution_time * 1000, 2)
            if self.min_execution_time != float("inf")
            else 0,
            "max_execution_time_ms": round(self.max_execution_time * 1000, 2),
        }


class EvaluationStore:
    """
    Store for evaluation records and feedback.

    In production, this would be backed by a database.
    """

    def __init__(self):
        self._records: list[EvaluationRecord] = []
        self._confusion_matrices: dict[str, ConfusionMatrix] = defaultdict(ConfusionMatrix)
        self._agent_metrics: dict[str, AgentPerformanceMetrics] = {}
        self._negative_exemplars: list[dict[str, Any]] = []  # For feedback loop

    def add_record(self, record: EvaluationRecord):
        """Add an evaluation record."""
        self._records.append(record)

        if record.actual_outcome:
            self._confusion_matrices["overall"].add_outcome(record.actual_outcome)
            self._confusion_matrices[record.entity_type].add_outcome(record.actual_outcome)

            # Store negative exemplars for feedback loop
            if record.actual_outcome in (
                EvaluationOutcome.FALSE_POSITIVE,
                EvaluationOutcome.FALSE_NEGATIVE,
            ):
                self._negative_exemplars.append(record.to_dict())
                logger.info(
                    f"Stored negative exemplar for alert {record.alert_id}: {record.actual_outcome.value}"
                )

    def record_agent_execution(self, agent_name: str, success: bool, execution_time: float):
        """Record an agent execution for performance tracking."""
        if agent_name not in self._agent_metrics:
            self._agent_metrics[agent_name] = AgentPerformanceMetrics(agent_name)
        self._agent_metrics[agent_name].record_execution(success, execution_time)

    def get_confusion_matrix(self, entity_type: Optional[str] = None) -> ConfusionMatrix:
        """Get confusion matrix, optionally filtered by entity type."""
        key = entity_type or "overall"
        return self._confusion_matrices[key]

    def get_agent_metrics(
        self, agent_name: Optional[str] = None
    ) -> dict[str, AgentPerformanceMetrics]:
        """Get agent performance metrics."""
        if agent_name:
            return {
                agent_name: self._agent_metrics.get(agent_name, AgentPerformanceMetrics(agent_name))
            }
        return self._agent_metrics

    def get_negative_exemplars(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent negative exemplars for feedback loop."""
        return self._negative_exemplars[-limit:]

    def get_summary_report(self) -> dict[str, Any]:
        """Generate a summary evaluation report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_evaluated": len(self._records),
            "overall_metrics": self._confusion_matrices["overall"].to_dict(),
            "metrics_by_entity_type": {
                entity_type: matrix.to_dict()
                for entity_type, matrix in self._confusion_matrices.items()
                if entity_type != "overall"
            },
            "agent_performance": {
                name: metrics.to_dict() for name, metrics in self._agent_metrics.items()
            },
            "negative_exemplar_count": len(self._negative_exemplars),
        }


class FeedbackLoop:
    """
    Implements feedback loop for continuous improvement.

    When human analysts overrule the agent, this feedback is stored
    and can be used to improve future decisions.
    """

    def __init__(self, store: Optional[EvaluationStore] = None):
        self.store = store or EvaluationStore()

    def record_human_override(
        self,
        alert_id: str,
        entity_type: str,
        agent_decision: str,
        human_decision: str,
        risk_score: float,
        confidence: float,
        reason: str = "",
    ):
        """
        Record when a human analyst overrules the agent.

        This creates a negative exemplar that can be used to improve
        future decision-making.
        """
        # Determine the actual outcome
        if agent_decision in ("block", "freeze_account") and human_decision == "approve":
            outcome = EvaluationOutcome.FALSE_POSITIVE
        elif agent_decision == "approve" and human_decision in ("block", "freeze_account"):
            outcome = EvaluationOutcome.FALSE_NEGATIVE
        else:
            outcome = None  # Decision modified but not a clear error

        record = EvaluationRecord(
            alert_id=alert_id,
            entity_type=entity_type,
            predicted_action=agent_decision,
            predicted_risk_score=risk_score,
            predicted_confidence=confidence,
            actual_outcome=outcome,
            human_decision=human_decision,
            feedback_source="human_review",
            notes=reason,
        )

        self.store.add_record(record)

        logger.info(
            f"Human override recorded for {alert_id}: "
            f"agent={agent_decision}, human={human_decision}, outcome={outcome}"
        )

        return record

    def record_chargeback(
        self,
        alert_id: str,
        entity_type: str,
        original_decision: str,
        risk_score: float,
        confidence: float,
    ):
        """
        Record when a chargeback occurs (indicates fraud was missed).
        """
        record = EvaluationRecord(
            alert_id=alert_id,
            entity_type=entity_type,
            predicted_action=original_decision,
            predicted_risk_score=risk_score,
            predicted_confidence=confidence,
            actual_outcome=EvaluationOutcome.FALSE_NEGATIVE,
            feedback_source="chargeback",
            notes="Fraud confirmed via chargeback",
        )

        self.store.add_record(record)

        logger.warning(f"Chargeback recorded for {alert_id} - FALSE NEGATIVE")

        return record

    def record_user_confirmation(
        self,
        alert_id: str,
        entity_type: str,
        original_decision: str,
        risk_score: float,
        confidence: float,
        was_legitimate: bool,
    ):
        """
        Record when a user confirms or denies activity.
        """
        if original_decision in ("block", "request_mfa", "freeze_account"):
            outcome = (
                EvaluationOutcome.FALSE_POSITIVE
                if was_legitimate
                else EvaluationOutcome.TRUE_POSITIVE
            )
        else:
            outcome = (
                EvaluationOutcome.TRUE_NEGATIVE
                if was_legitimate
                else EvaluationOutcome.FALSE_NEGATIVE
            )

        record = EvaluationRecord(
            alert_id=alert_id,
            entity_type=entity_type,
            predicted_action=original_decision,
            predicted_risk_score=risk_score,
            predicted_confidence=confidence,
            actual_outcome=outcome,
            feedback_source="user_confirmation",
            notes=f"User confirmed {'legitimate' if was_legitimate else 'fraudulent'}",
        )

        self.store.add_record(record)

        return record

    def get_improvement_suggestions(self) -> list[dict[str, Any]]:
        """
        Analyze negative exemplars and generate improvement suggestions.
        """
        exemplars = self.store.get_negative_exemplars()
        suggestions = []

        # Analyze false positives
        false_positives = [e for e in exemplars if e.get("actual_outcome") == "false_positive"]
        if len(false_positives) > 5:
            avg_risk = sum(e.get("predicted_risk_score", 0) for e in false_positives) / len(
                false_positives
            )
            suggestions.append(
                {
                    "type": "threshold_adjustment",
                    "issue": "High false positive rate",
                    "details": f"{len(false_positives)} false positives detected",
                    "suggestion": f"Consider raising block threshold. Avg risk score was {avg_risk:.1f}",
                }
            )

        # Analyze false negatives
        false_negatives = [e for e in exemplars if e.get("actual_outcome") == "false_negative"]
        if len(false_negatives) > 3:
            avg_risk = sum(e.get("predicted_risk_score", 0) for e in false_negatives) / len(
                false_negatives
            )
            suggestions.append(
                {
                    "type": "sensitivity_adjustment",
                    "issue": "False negatives detected",
                    "details": f"{len(false_negatives)} fraudulent activities were missed",
                    "suggestion": f"Review detection rules. Avg risk score was {avg_risk:.1f}",
                }
            )

        # Analyze confidence calibration
        low_confidence_errors = [e for e in exemplars if e.get("predicted_confidence", 1.0) < 0.5]
        if len(low_confidence_errors) > 0:
            suggestions.append(
                {
                    "type": "confidence_calibration",
                    "issue": "Low confidence decisions leading to errors",
                    "details": f"{len(low_confidence_errors)} errors on low-confidence decisions",
                    "suggestion": "Consider mandatory human review for confidence < 0.5",
                }
            )

        return suggestions


# Global instances
_evaluation_store: Optional[EvaluationStore] = None
_feedback_loop: Optional[FeedbackLoop] = None


def get_evaluation_store() -> EvaluationStore:
    """Get the global evaluation store."""
    global _evaluation_store
    if _evaluation_store is None:
        _evaluation_store = EvaluationStore()
    return _evaluation_store


def get_feedback_loop() -> FeedbackLoop:
    """Get the global feedback loop."""
    global _feedback_loop
    if _feedback_loop is None:
        _feedback_loop = FeedbackLoop(get_evaluation_store())
    return _feedback_loop
