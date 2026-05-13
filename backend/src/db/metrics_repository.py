"""
Repository for observability and metrics persistence.
Handles CRUD operations for metrics, evaluations, and LLM usage tracking.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from db.models import (
    MetricSnapshot,
    AgentPerformance,
    EvaluationRecord,
    ConfusionMatrixSnapshot,
    LLMUsageRecord,
    LLMUsageSummary,
    EvaluationOutcomeType,
)

logger = logging.getLogger(__name__)


class MetricsRepository:
    """Repository for system metrics persistence."""

    def __init__(self, db: Session):
        self.db = db

    def record_metrics_snapshot(
        self,
        timestamp: datetime,
        granularity: str,
        alerts_received: int = 0,
        alerts_processed: int = 0,
        decisions_total: int = 0,
        decisions_allow: int = 0,
        decisions_block: int = 0,
        decisions_review: int = 0,
        escalations_total: int = 0,
        escalations_pending: int = 0,
        avg_processing_time_ms: float = 0.0,
        risk_scores: Optional[Dict[str, int]] = None,
    ) -> MetricSnapshot:
        """Record a metrics snapshot (upsert)."""

        # Truncate timestamp to granularity
        if granularity == "minute":
            timestamp = timestamp.replace(second=0, microsecond=0)
        elif granularity == "hour":
            timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        elif granularity == "day":
            timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check if exists
        existing = (
            self.db.query(MetricSnapshot)
            .filter(
                MetricSnapshot.timestamp == timestamp,
                MetricSnapshot.granularity == granularity,
            )
            .first()
        )

        if existing:
            # Update existing
            existing.alerts_received += alerts_received
            existing.alerts_processed += alerts_processed
            existing.decisions_total += decisions_total
            existing.decisions_allow += decisions_allow
            existing.decisions_block += decisions_block
            existing.decisions_review += decisions_review
            existing.escalations_total += escalations_total
            existing.escalations_pending = escalations_pending
            self.db.commit()
            return existing
        else:
            # Create new
            snapshot = MetricSnapshot(
                timestamp=timestamp,
                granularity=granularity,
                alerts_received=alerts_received,
                alerts_processed=alerts_processed,
                decisions_total=decisions_total,
                decisions_allow=decisions_allow,
                decisions_block=decisions_block,
                decisions_review=decisions_review,
                escalations_total=escalations_total,
                escalations_pending=escalations_pending,
                avg_processing_time_ms=avg_processing_time_ms,
                risk_scores=risk_scores or {},
            )
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)
            return snapshot

    def get_metrics_history(
        self,
        granularity: str = "hour",
        hours: int = 24,
    ) -> List[MetricSnapshot]:
        """Get metrics history for the specified period."""
        since = datetime.utcnow() - timedelta(hours=hours)

        return (
            self.db.query(MetricSnapshot)
            .filter(
                MetricSnapshot.granularity == granularity,
                MetricSnapshot.timestamp >= since,
            )
            .order_by(MetricSnapshot.timestamp.desc())
            .all()
        )

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current aggregated metrics."""
        # Get today's totals
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        result = (
            self.db.query(
                func.sum(MetricSnapshot.alerts_received).label("alerts_received"),
                func.sum(MetricSnapshot.alerts_processed).label("alerts_processed"),
                func.sum(MetricSnapshot.decisions_total).label("decisions_total"),
                func.sum(MetricSnapshot.decisions_allow).label("decisions_allow"),
                func.sum(MetricSnapshot.decisions_block).label("decisions_block"),
                func.sum(MetricSnapshot.decisions_review).label("decisions_review"),
                func.sum(MetricSnapshot.escalations_total).label("escalations_total"),
            )
            .filter(
                MetricSnapshot.timestamp >= today,
            )
            .first()
        )

        return {
            "alerts": {
                "received": result.alerts_received or 0,
                "processed": result.alerts_processed or 0,
            },
            "decisions": {
                "total": result.decisions_total or 0,
                "allow": result.decisions_allow or 0,
                "block": result.decisions_block or 0,
                "review": result.decisions_review or 0,
            },
            "escalations": {
                "total": result.escalations_total or 0,
            },
        }


class AgentPerformanceRepository:
    """Repository for agent performance metrics."""

    def __init__(self, db: Session):
        self.db = db

    def record_execution(
        self,
        agent_name: str,
        success: bool,
        execution_time_ms: float,
        timestamp: Optional[datetime] = None,
        granularity: str = "hour",
    ) -> AgentPerformance:
        """Record an agent execution."""
        timestamp = timestamp or datetime.utcnow()

        # Truncate to granularity
        if granularity == "hour":
            timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        elif granularity == "day":
            timestamp = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check if exists
        existing = (
            self.db.query(AgentPerformance)
            .filter(
                AgentPerformance.agent_name == agent_name,
                AgentPerformance.timestamp == timestamp,
                AgentPerformance.granularity == granularity,
            )
            .first()
        )

        if existing:
            existing.total_executions += 1
            if success:
                existing.successful_executions += 1
            else:
                existing.failed_executions += 1
            existing.total_execution_time_ms += execution_time_ms
            existing.min_execution_time_ms = min(
                existing.min_execution_time_ms or float("inf"), execution_time_ms
            )
            existing.max_execution_time_ms = max(
                existing.max_execution_time_ms or 0, execution_time_ms
            )
            existing.avg_execution_time_ms = (
                existing.total_execution_time_ms / existing.total_executions
            )
            self.db.commit()
            return existing
        else:
            perf = AgentPerformance(
                timestamp=timestamp,
                granularity=granularity,
                agent_name=agent_name,
                total_executions=1,
                successful_executions=1 if success else 0,
                failed_executions=0 if success else 1,
                total_execution_time_ms=execution_time_ms,
                min_execution_time_ms=execution_time_ms,
                max_execution_time_ms=execution_time_ms,
                avg_execution_time_ms=execution_time_ms,
            )
            self.db.add(perf)
            self.db.commit()
            self.db.refresh(perf)
            return perf

    def get_agent_performance(
        self,
        agent_name: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Dict[str, Any]]:
        """Get aggregated agent performance."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(
            AgentPerformance.agent_name,
            func.sum(AgentPerformance.total_executions).label("total_executions"),
            func.sum(AgentPerformance.successful_executions).label("successful_executions"),
            func.sum(AgentPerformance.failed_executions).label("failed_executions"),
            func.avg(AgentPerformance.avg_execution_time_ms).label("avg_execution_time_ms"),
            func.min(AgentPerformance.min_execution_time_ms).label("min_execution_time_ms"),
            func.max(AgentPerformance.max_execution_time_ms).label("max_execution_time_ms"),
        ).filter(
            AgentPerformance.timestamp >= since,
        )

        if agent_name:
            query = query.filter(AgentPerformance.agent_name == agent_name)

        results = query.group_by(AgentPerformance.agent_name).all()

        return {
            r.agent_name: {
                "agent_name": r.agent_name,
                "total_executions": r.total_executions or 0,
                "success_rate": (r.successful_executions or 0) / (r.total_executions or 1),
                "avg_execution_time_ms": round(r.avg_execution_time_ms or 0, 2),
                "min_execution_time_ms": round(r.min_execution_time_ms or 0, 2),
                "max_execution_time_ms": round(r.max_execution_time_ms or 0, 2),
            }
            for r in results
        }


class EvaluationRepository:
    """Repository for evaluation records and confusion matrix."""

    def __init__(self, db: Session):
        self.db = db

    def record_prediction(
        self,
        entity_id: str,
        entity_type: str,
        predicted_action: str,
        predicted_risk_score: float,
        predicted_confidence: float = 0.8,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        prediction_id: Optional[str] = None,
    ) -> EvaluationRecord:
        """Record a prediction for later evaluation."""
        record = EvaluationRecord(
            prediction_id=prediction_id or str(uuid4()),
            entity_id=entity_id,
            entity_type=entity_type,
            predicted_action=predicted_action,
            predicted_risk_score=predicted_risk_score,
            predicted_confidence=predicted_confidence,
            model_name=model_name,
            model_version=model_version,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def record_outcome(
        self,
        entity_id: str,
        actual_outcome: EvaluationOutcomeType,
        feedback_source: str,
        human_decision: Optional[str] = None,
        notes: Optional[str] = None,
        prediction_id: Optional[str] = None,
    ) -> Optional[EvaluationRecord]:
        """Record the actual outcome for a prediction."""
        # Find the prediction
        query = self.db.query(EvaluationRecord)
        if prediction_id:
            query = query.filter(EvaluationRecord.prediction_id == prediction_id)
        else:
            query = query.filter(EvaluationRecord.entity_id == entity_id)

        record = (
            query.filter(EvaluationRecord.actual_outcome.is_(None))
            .order_by(EvaluationRecord.created_at.desc())
            .first()
        )

        if record:
            record.actual_outcome = actual_outcome
            record.feedback_source = feedback_source
            record.human_decision = human_decision
            record.notes = notes
            record.feedback_received_at = datetime.utcnow()
            self.db.commit()
            return record

        return None

    def get_confusion_matrix(
        self,
        entity_type: Optional[str] = None,
        hours: int = 24 * 30,  # Default: last 30 days
    ) -> Dict[str, Any]:
        """Calculate confusion matrix from evaluation records."""
        since = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(
            EvaluationRecord.actual_outcome,
            func.count(EvaluationRecord.id).label("count"),
        ).filter(
            EvaluationRecord.actual_outcome.isnot(None),
            EvaluationRecord.created_at >= since,
        )

        if entity_type:
            query = query.filter(EvaluationRecord.entity_type == entity_type)

        results = query.group_by(EvaluationRecord.actual_outcome).all()

        matrix = {
            "true_positives": 0,
            "true_negatives": 0,
            "false_positives": 0,
            "false_negatives": 0,
        }

        for r in results:
            if r.actual_outcome == EvaluationOutcomeType.TRUE_POSITIVE:
                matrix["true_positives"] = r.count
            elif r.actual_outcome == EvaluationOutcomeType.TRUE_NEGATIVE:
                matrix["true_negatives"] = r.count
            elif r.actual_outcome == EvaluationOutcomeType.FALSE_POSITIVE:
                matrix["false_positives"] = r.count
            elif r.actual_outcome == EvaluationOutcomeType.FALSE_NEGATIVE:
                matrix["false_negatives"] = r.count

        # Calculate metrics
        tp, tn, fp, fn = (
            matrix["true_positives"],
            matrix["true_negatives"],
            matrix["false_positives"],
            matrix["false_negatives"],
        )
        total = tp + tn + fp + fn

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / total if total > 0 else 0

        return {
            **matrix,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "total_evaluated": total,
        }

    def get_evaluation_summary(
        self,
        hours: int = 24 * 30,
    ) -> Dict[str, Any]:
        """Get evaluation summary report."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # Total records
        total_evaluated = (
            self.db.query(func.count(EvaluationRecord.id))
            .filter(
                EvaluationRecord.actual_outcome.isnot(None),
                EvaluationRecord.created_at >= since,
            )
            .scalar()
            or 0
        )

        total_pending = (
            self.db.query(func.count(EvaluationRecord.id))
            .filter(
                EvaluationRecord.actual_outcome.is_(None),
                EvaluationRecord.created_at >= since,
            )
            .scalar()
            or 0
        )

        # Negative exemplars (errors)
        negative_exemplars = (
            self.db.query(func.count(EvaluationRecord.id))
            .filter(
                EvaluationRecord.actual_outcome.in_(
                    [
                        EvaluationOutcomeType.FALSE_POSITIVE,
                        EvaluationOutcomeType.FALSE_NEGATIVE,
                    ]
                ),
                EvaluationRecord.created_at >= since,
            )
            .scalar()
            or 0
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_evaluated": total_evaluated,
            "total_pending": total_pending,
            "negative_exemplar_count": negative_exemplars,
            "overall_metrics": self.get_confusion_matrix(),
        }


class LLMUsageRepository:
    """Repository for LLM usage tracking."""

    def __init__(self, db: Session):
        self.db = db

    def record_call(
        self,
        call_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        input_cost: float,
        output_cost: float,
        total_cost: float,
        latency_ms: float,
        success: bool,
        agent_name: str,
        operation: str,
        entity_id: Optional[str] = None,
        error_message: Optional[str] = None,
        provider: Optional[str] = None,
        request_metadata: Optional[Dict] = None,
    ) -> LLMUsageRecord:
        """Record an LLM API call."""
        record = LLMUsageRecord(
            call_id=call_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            agent_name=agent_name,
            operation=operation,
            entity_id=entity_id,
            request_metadata=request_metadata,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        # Also update hourly summary
        self._update_summary(record)

        return record

    def _update_summary(self, record: LLMUsageRecord):
        """Update the hourly summary."""
        timestamp = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        # Overall summary
        self._upsert_summary(timestamp, None, None, record)

        # By model summary
        self._upsert_summary(timestamp, record.model, None, record)

        # By agent summary
        self._upsert_summary(timestamp, None, record.agent_name, record)

    def _upsert_summary(
        self,
        timestamp: datetime,
        model: Optional[str],
        agent_name: Optional[str],
        record: LLMUsageRecord,
    ):
        """Upsert a summary record."""
        existing = (
            self.db.query(LLMUsageSummary)
            .filter(
                LLMUsageSummary.timestamp == timestamp,
                LLMUsageSummary.granularity == "hour",
                LLMUsageSummary.model == model,
                LLMUsageSummary.agent_name == agent_name,
            )
            .first()
        )

        if existing:
            existing.total_calls += 1
            if record.success:
                existing.successful_calls += 1
            else:
                existing.failed_calls += 1
            existing.total_input_tokens += record.input_tokens
            existing.total_output_tokens += record.output_tokens
            existing.total_tokens += record.total_tokens
            existing.total_cost += record.total_cost
            existing.min_latency_ms = min(
                existing.min_latency_ms or float("inf"), record.latency_ms
            )
            existing.max_latency_ms = max(existing.max_latency_ms or 0, record.latency_ms)
            existing.avg_latency_ms = (
                (existing.avg_latency_ms or 0) * (existing.total_calls - 1) + record.latency_ms
            ) / existing.total_calls
        else:
            summary = LLMUsageSummary(
                timestamp=timestamp,
                granularity="hour",
                model=model,
                agent_name=agent_name,
                total_calls=1,
                successful_calls=1 if record.success else 0,
                failed_calls=0 if record.success else 1,
                total_input_tokens=record.input_tokens,
                total_output_tokens=record.output_tokens,
                total_tokens=record.total_tokens,
                total_cost=record.total_cost,
                avg_latency_ms=record.latency_ms,
                min_latency_ms=record.latency_ms,
                max_latency_ms=record.latency_ms,
            )
            self.db.add(summary)

        self.db.commit()

    def get_usage_stats(
        self,
        hours: int = 24,
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get aggregated LLM usage statistics."""
        since = datetime.utcnow() - timedelta(hours=hours)

        # Base query
        query = self.db.query(
            func.sum(LLMUsageSummary.total_calls).label("total_calls"),
            func.sum(LLMUsageSummary.successful_calls).label("successful_calls"),
            func.sum(LLMUsageSummary.failed_calls).label("failed_calls"),
            func.sum(LLMUsageSummary.total_input_tokens).label("total_input_tokens"),
            func.sum(LLMUsageSummary.total_output_tokens).label("total_output_tokens"),
            func.sum(LLMUsageSummary.total_tokens).label("total_tokens"),
            func.sum(LLMUsageSummary.total_cost).label("total_cost"),
            func.avg(LLMUsageSummary.avg_latency_ms).label("avg_latency_ms"),
            func.min(LLMUsageSummary.min_latency_ms).label("min_latency_ms"),
            func.max(LLMUsageSummary.max_latency_ms).label("max_latency_ms"),
        ).filter(
            LLMUsageSummary.timestamp >= since,
            LLMUsageSummary.model.is_(None),  # Get overall summary
            LLMUsageSummary.agent_name.is_(None),
        )

        result = query.first()

        if not result or not result.total_calls:
            return {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "success_rate": 0,
                "tokens": {"input": 0, "output": 0, "total": 0, "avg_per_call": 0},
                "cost": {"total_usd": 0, "avg_per_call_usd": 0},
                "latency": {"avg_ms": 0, "min_ms": 0, "max_ms": 0},
                "by_model": {},
                "by_agent": {},
            }

        total_calls = result.total_calls or 0

        # Get by-model breakdown
        by_model = {}
        model_results = (
            self.db.query(
                LLMUsageSummary.model,
                func.sum(LLMUsageSummary.total_calls).label("calls"),
                func.sum(LLMUsageSummary.total_tokens).label("tokens"),
                func.sum(LLMUsageSummary.total_cost).label("cost"),
            )
            .filter(
                LLMUsageSummary.timestamp >= since,
                LLMUsageSummary.model.isnot(None),
                LLMUsageSummary.agent_name.is_(None),
            )
            .group_by(LLMUsageSummary.model)
            .all()
        )

        for r in model_results:
            by_model[r.model] = {
                "calls": r.calls,
                "tokens": r.tokens,
                "cost": round(r.cost, 4),
            }

        # Get by-agent breakdown
        by_agent = {}
        agent_results = (
            self.db.query(
                LLMUsageSummary.agent_name,
                func.sum(LLMUsageSummary.total_calls).label("calls"),
                func.sum(LLMUsageSummary.total_tokens).label("tokens"),
                func.sum(LLMUsageSummary.total_cost).label("cost"),
            )
            .filter(
                LLMUsageSummary.timestamp >= since,
                LLMUsageSummary.agent_name.isnot(None),
                LLMUsageSummary.model.is_(None),
            )
            .group_by(LLMUsageSummary.agent_name)
            .all()
        )

        for r in agent_results:
            by_agent[r.agent_name] = {
                "calls": r.calls,
                "tokens": r.tokens,
                "cost": round(r.cost, 4),
            }

        return {
            "total_calls": total_calls,
            "successful_calls": result.successful_calls or 0,
            "failed_calls": result.failed_calls or 0,
            "success_rate": round((result.successful_calls or 0) / total_calls, 4)
            if total_calls
            else 0,
            "tokens": {
                "input": result.total_input_tokens or 0,
                "output": result.total_output_tokens or 0,
                "total": result.total_tokens or 0,
                "avg_per_call": round((result.total_tokens or 0) / total_calls, 1)
                if total_calls
                else 0,
            },
            "cost": {
                "total_usd": round(result.total_cost or 0, 4),
                "avg_per_call_usd": round((result.total_cost or 0) / total_calls, 6)
                if total_calls
                else 0,
            },
            "latency": {
                "avg_ms": round(result.avg_latency_ms or 0, 2),
                "min_ms": round(result.min_latency_ms or 0, 2),
                "max_ms": round(result.max_latency_ms or 0, 2),
            },
            "by_model": by_model,
            "by_agent": by_agent,
        }

    def get_recent_calls(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent LLM calls."""
        records = (
            self.db.query(LLMUsageRecord)
            .order_by(LLMUsageRecord.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "call_id": r.call_id,
                "model": r.model,
                "timestamp": r.created_at.isoformat(),
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "total_cost": round(r.total_cost, 6),
                "latency_ms": round(r.latency_ms, 2),
                "success": r.success,
                "agent_name": r.agent_name,
                "operation": r.operation,
            }
            for r in records
        ]

    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly usage breakdown."""
        since = datetime.utcnow() - timedelta(hours=hours)

        results = (
            self.db.query(
                LLMUsageSummary.timestamp,
                LLMUsageSummary.total_calls,
                LLMUsageSummary.total_tokens,
                LLMUsageSummary.total_cost,
            )
            .filter(
                LLMUsageSummary.timestamp >= since,
                LLMUsageSummary.model.is_(None),
                LLMUsageSummary.agent_name.is_(None),
            )
            .order_by(LLMUsageSummary.timestamp)
            .all()
        )

        return [
            {
                "hour": r.timestamp.strftime("%Y-%m-%d %H:00"),
                "calls": r.total_calls,
                "tokens": r.total_tokens,
                "cost": round(r.total_cost, 4),
            }
            for r in results
        ]
