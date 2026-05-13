"""
Metrics Persistence Layer for Fraud Detection System.

Bridges in-memory FraudMetrics to PostgreSQL for historical tracking.
Supports periodic snapshots and real-time persistence.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PersistenceInterval(str, Enum):
    """Supported persistence intervals."""

    MINUTE = "minute"
    FIVE_MINUTES = "5min"
    FIFTEEN_MINUTES = "15min"
    HOUR = "hour"


@dataclass
class PersistenceConfig:
    """Configuration for metrics persistence."""

    # Enable/disable persistence
    enabled: bool = True

    # Interval for periodic snapshots
    interval: PersistenceInterval = PersistenceInterval.MINUTE

    # Granularities to store (minute, hour, day)
    granularities: tuple = ("minute", "hour", "day")

    # Retain data for how many days
    retention_days: int = 90

    # Batch size for bulk inserts
    batch_size: int = 100

    # Persist agent performance metrics
    persist_agent_performance: bool = True

    # Persist immediately on each event (vs. only periodic)
    persist_on_event: bool = False

    @classmethod
    def from_env(cls) -> "PersistenceConfig":
        """Create config from environment variables."""
        import os

        return cls(
            enabled=os.getenv("METRICS_PERSISTENCE_ENABLED", "true").lower() == "true",
            interval=PersistenceInterval(os.getenv("METRICS_PERSISTENCE_INTERVAL", "minute")),
            retention_days=int(os.getenv("METRICS_RETENTION_DAYS", "90")),
            persist_on_event=os.getenv("METRICS_PERSIST_ON_EVENT", "false").lower() == "true",
        )


class MetricsPersistence:
    """
    Persists in-memory metrics to PostgreSQL.

    This class bridges the gap between the fast in-memory FraudMetrics
    and the database for historical tracking and querying.

    Features:
    - Periodic snapshot persistence (configurable interval)
    - Multiple granularities (minute, hour, day)
    - Agent performance tracking
    - Thread-safe operation
    - Graceful degradation when database unavailable
    """

    def __init__(self, config: Optional[PersistenceConfig] = None):
        self.config = config or PersistenceConfig()
        self._lock = threading.Lock()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._last_snapshot: Optional[datetime] = None
        self._db_available = False
        self._callbacks: Dict[str, Callable] = {}

        # Track last persisted values for delta calculation
        self._last_values: Dict[str, Any] = {}

        # Initialize database connection check
        self._check_db_availability()

    def _check_db_availability(self):
        """Check if database is available."""
        try:
            from db.session import get_session_factory, SQLALCHEMY_AVAILABLE

            if not SQLALCHEMY_AVAILABLE:
                self._db_available = False
                logger.info("Metrics persistence: SQLAlchemy not available")
                return

            factory = get_session_factory()
            self._db_available = factory is not None
            if self._db_available:
                logger.info("Metrics persistence: Database connection available")
            else:
                logger.warning("Metrics persistence: Database not configured")
        except Exception as e:
            self._db_available = False
            logger.warning(f"Metrics persistence: Database check failed - {e}")

    def _get_db_session(self):
        """Get a database session."""
        if not self._db_available:
            return None
        try:
            from db.session import get_session_factory

            SessionLocal = get_session_factory()
            if SessionLocal:
                return SessionLocal()
        except Exception as e:
            logger.warning(f"Failed to get DB session: {e}")
        return None

    @property
    def is_available(self) -> bool:
        """Check if persistence is available and enabled."""
        return self.config.enabled and self._db_available

    def start(self):
        """Start the periodic persistence scheduler."""
        if not self.config.enabled:
            logger.info("Metrics persistence is disabled")
            return

        if not self._db_available:
            logger.warning("Database not available, periodic persistence disabled")
            return

        if self._running:
            logger.warning("Metrics persistence scheduler already running")
            return

        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True, name="metrics-persistence-scheduler"
        )
        self._scheduler_thread.start()
        logger.info(
            f"Metrics persistence scheduler started (interval: {self.config.interval.value})"
        )

    def stop(self):
        """Stop the periodic persistence scheduler."""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None
        logger.info("Metrics persistence scheduler stopped")

    def _get_interval_seconds(self) -> int:
        """Get the interval in seconds based on config."""
        intervals = {
            PersistenceInterval.MINUTE: 60,
            PersistenceInterval.FIVE_MINUTES: 300,
            PersistenceInterval.FIFTEEN_MINUTES: 900,
            PersistenceInterval.HOUR: 3600,
        }
        return intervals.get(self.config.interval, 60)

    def _scheduler_loop(self):
        """Main loop for periodic persistence."""
        interval = self._get_interval_seconds()

        while self._running:
            try:
                # Wait for next interval
                time.sleep(interval)

                if not self._running:
                    break

                # Take and persist snapshot
                self.persist_snapshot()

            except Exception as e:
                logger.error(f"Error in persistence scheduler: {e}")

    def persist_snapshot(self, timestamp: Optional[datetime] = None):
        """
        Persist current metrics snapshot to database.

        Args:
            timestamp: Optional timestamp for the snapshot (defaults to now)
        """
        if not self.is_available:
            return

        timestamp = timestamp or datetime.utcnow()

        db = self._get_db_session()
        if not db:
            return

        try:
            # Get current metrics from FraudMetrics
            from observability.metrics import get_fraud_metrics

            metrics = get_fraud_metrics()

            # Persist to each configured granularity
            for granularity in self.config.granularities:
                self._persist_metrics_snapshot(db, metrics, timestamp, granularity)

            # Persist agent performance if enabled
            if self.config.persist_agent_performance:
                self._persist_agent_performance(db, metrics, timestamp)

            self._last_snapshot = timestamp
            logger.debug(f"Metrics snapshot persisted at {timestamp}")

        except Exception as e:
            logger.error(f"Failed to persist metrics snapshot: {e}")
            db.rollback()
        finally:
            db.close()

    def _persist_metrics_snapshot(self, db, metrics, timestamp: datetime, granularity: str):
        """Persist metrics to MetricSnapshot table."""
        from db.metrics_repository import MetricsRepository

        repo = MetricsRepository(db)

        # Calculate current values from in-memory metrics
        alerts_received = int(metrics.alerts_received.total())
        alerts_processed = int(metrics.alerts_processed.total())

        # Get decision counts by action
        decisions_total = int(metrics.decisions_made.total())
        decisions_allow = (
            int(metrics.decisions_made.get(labels={"action": "allow", "confidence_level": "high"}))
            + int(
                metrics.decisions_made.get(labels={"action": "allow", "confidence_level": "medium"})
            )
            + int(metrics.decisions_made.get(labels={"action": "allow", "confidence_level": "low"}))
        )
        decisions_block = (
            int(metrics.decisions_made.get(labels={"action": "block", "confidence_level": "high"}))
            + int(
                metrics.decisions_made.get(labels={"action": "block", "confidence_level": "medium"})
            )
            + int(metrics.decisions_made.get(labels={"action": "block", "confidence_level": "low"}))
        )
        decisions_review = (
            int(metrics.decisions_made.get(labels={"action": "review", "confidence_level": "high"}))
            + int(
                metrics.decisions_made.get(
                    labels={"action": "review", "confidence_level": "medium"}
                )
            )
            + int(
                metrics.decisions_made.get(labels={"action": "review", "confidence_level": "low"})
            )
        )

        # Get escalation metrics
        escalations_total = int(metrics.escalations.total())
        escalations_pending = int(metrics.pending_escalations.total())

        # Get processing time stats
        processing_stats = metrics.alert_processing_time.get_stats()
        avg_processing_time_ms = processing_stats.get("mean", 0.0) * 1000  # Convert to ms

        # Get risk score distribution
        risk_stats = metrics.risk_scores.get_stats()
        risk_buckets = risk_stats.get("buckets", {})
        risk_scores = {
            "low": sum(risk_buckets.get(b, 0) for b in [10, 20, 30]),
            "medium": sum(risk_buckets.get(b, 0) for b in [40, 50, 60]),
            "high": sum(risk_buckets.get(b, 0) for b in [70, 80]),
            "critical": sum(risk_buckets.get(b, 0) for b in [90, 100]),
        }

        # Calculate delta from last persisted values
        key = f"snapshot_{granularity}"
        last = self._last_values.get(key, {})

        delta_alerts_received = alerts_received - last.get("alerts_received", 0)
        delta_alerts_processed = alerts_processed - last.get("alerts_processed", 0)
        delta_decisions_total = decisions_total - last.get("decisions_total", 0)
        delta_decisions_allow = decisions_allow - last.get("decisions_allow", 0)
        delta_decisions_block = decisions_block - last.get("decisions_block", 0)
        delta_decisions_review = decisions_review - last.get("decisions_review", 0)
        delta_escalations = escalations_total - last.get("escalations_total", 0)

        # Only persist if there's new data or it's the first snapshot
        if any(
            [
                delta_alerts_received,
                delta_alerts_processed,
                delta_decisions_total,
                delta_escalations,
                not last,  # First snapshot
            ]
        ):
            repo.record_metrics_snapshot(
                timestamp=timestamp,
                granularity=granularity,
                alerts_received=max(0, delta_alerts_received),
                alerts_processed=max(0, delta_alerts_processed),
                decisions_total=max(0, delta_decisions_total),
                decisions_allow=max(0, delta_decisions_allow),
                decisions_block=max(0, delta_decisions_block),
                decisions_review=max(0, delta_decisions_review),
                escalations_total=max(0, delta_escalations),
                escalations_pending=escalations_pending,
                avg_processing_time_ms=avg_processing_time_ms,
                risk_scores=risk_scores,
            )

        # Update last values for delta calculation
        self._last_values[key] = {
            "alerts_received": alerts_received,
            "alerts_processed": alerts_processed,
            "decisions_total": decisions_total,
            "decisions_allow": decisions_allow,
            "decisions_block": decisions_block,
            "decisions_review": decisions_review,
            "escalations_total": escalations_total,
        }

    def _persist_agent_performance(self, db, metrics, timestamp: datetime):
        """Persist agent performance metrics."""
        from db.metrics_repository import AgentPerformanceRepository

        repo = AgentPerformanceRepository(db)

        # Get execution time histogram
        exec_time = metrics.agent_execution_time

        # Iterate through all agent labels
        for label_values, total_count in exec_time._totals.items():
            if not label_values:
                continue

            agent_name = label_values[0]  # First label is agent_name

            # Get stats for this agent
            sum_time = exec_time._sums.get(label_values, 0.0)
            avg_time_ms = (sum_time / total_count * 1000) if total_count > 0 else 0

            # Get error count for this agent
            error_count = 0
            for error_labels, count in metrics.agent_errors._values.items():
                if error_labels and error_labels[0] == agent_name:
                    error_count += int(count)

            # Calculate delta
            key = f"agent_{agent_name}"
            last = self._last_values.get(key, {})
            delta_executions = total_count - last.get("total_executions", 0)
            delta_errors = error_count - last.get("error_count", 0)

            if delta_executions > 0:
                success = delta_executions - delta_errors
                repo.record_execution(
                    agent_name=agent_name,
                    success=success > 0,
                    execution_time_ms=avg_time_ms,
                    timestamp=timestamp,
                    granularity="hour",
                )

            # Update last values
            self._last_values[key] = {
                "total_executions": total_count,
                "error_count": error_count,
            }

    def persist_alert_received(
        self, entity_type: str, source: str, timestamp: Optional[datetime] = None
    ):
        """Persist individual alert received event (if persist_on_event is enabled)."""
        if not self.config.persist_on_event:
            return

        if not self.is_available:
            return

        # For event-based persistence, we just trigger a snapshot
        # This keeps it simple while still capturing real-time data
        self.persist_snapshot(timestamp)

    def persist_alert_processed(
        self,
        entity_type: str,
        severity: str,
        decision: str,
        processing_time: float,
        timestamp: Optional[datetime] = None,
    ):
        """Persist individual alert processed event (if persist_on_event is enabled)."""
        if not self.config.persist_on_event:
            return

        self.persist_snapshot(timestamp)

    def persist_agent_execution(
        self,
        agent_name: str,
        execution_time: float,
        success: bool,
        timestamp: Optional[datetime] = None,
    ):
        """
        Persist individual agent execution to database immediately.

        This is useful for real-time tracking of agent performance.
        """
        if not self.is_available:
            return

        db = self._get_db_session()
        if not db:
            return

        try:
            from db.metrics_repository import AgentPerformanceRepository

            repo = AgentPerformanceRepository(db)
            repo.record_execution(
                agent_name=agent_name,
                success=success,
                execution_time_ms=execution_time * 1000,  # Convert to ms
                timestamp=timestamp or datetime.utcnow(),
                granularity="hour",
            )
        except Exception as e:
            logger.warning(f"Failed to persist agent execution: {e}")
            db.rollback()
        finally:
            db.close()

    def persist_decision(
        self,
        entity_id: str,
        entity_type: str,
        action: str,
        risk_score: float,
        confidence: float,
        model_name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Persist a fraud decision for later evaluation.

        This creates an EvaluationRecord that can be updated later
        when the actual outcome is known.
        """
        if not self.is_available:
            return

        db = self._get_db_session()
        if not db:
            return

        try:
            from db.metrics_repository import EvaluationRepository

            repo = EvaluationRepository(db)
            repo.record_prediction(
                entity_id=entity_id,
                entity_type=entity_type,
                predicted_action=action,
                predicted_risk_score=risk_score,
                predicted_confidence=confidence,
                model_name=model_name,
            )
        except Exception as e:
            logger.warning(f"Failed to persist decision: {e}")
            db.rollback()
        finally:
            db.close()

    def get_metrics_history(self, granularity: str = "hour", hours: int = 24) -> Dict[str, Any]:
        """
        Get historical metrics from database.

        Args:
            granularity: Time bucket size (minute, hour, day)
            hours: Number of hours to look back

        Returns:
            Dictionary with historical metrics data
        """
        if not self.is_available:
            return {"error": "Database not available", "data": []}

        db = self._get_db_session()
        if not db:
            return {"error": "Could not get database session", "data": []}

        try:
            from db.metrics_repository import MetricsRepository

            repo = MetricsRepository(db)
            snapshots = repo.get_metrics_history(granularity=granularity, hours=hours)

            return {
                "granularity": granularity,
                "hours": hours,
                "data": [
                    {
                        "timestamp": s.timestamp.isoformat(),
                        "alerts_received": s.alerts_received,
                        "alerts_processed": s.alerts_processed,
                        "decisions": {
                            "total": s.decisions_total,
                            "allow": s.decisions_allow,
                            "block": s.decisions_block,
                            "review": s.decisions_review,
                        },
                        "escalations": {
                            "total": s.escalations_total,
                            "pending": s.escalations_pending,
                        },
                        "avg_processing_time_ms": s.avg_processing_time_ms,
                        "risk_scores": s.risk_scores,
                    }
                    for s in snapshots
                ],
            }
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return {"error": str(e), "data": []}
        finally:
            db.close()

    def get_agent_performance_history(
        self, agent_name: Optional[str] = None, hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get agent performance history from database.

        Args:
            agent_name: Optional filter by agent name
            hours: Number of hours to look back

        Returns:
            Dictionary with agent performance data
        """
        if not self.is_available:
            return {"error": "Database not available", "data": {}}

        db = self._get_db_session()
        if not db:
            return {"error": "Could not get database session", "data": {}}

        try:
            from db.metrics_repository import AgentPerformanceRepository

            repo = AgentPerformanceRepository(db)
            performance = repo.get_agent_performance(agent_name=agent_name, hours=hours)

            return {
                "hours": hours,
                "agent_filter": agent_name,
                "data": performance,
            }
        except Exception as e:
            logger.error(f"Failed to get agent performance: {e}")
            return {"error": str(e), "data": {}}
        finally:
            db.close()

    def get_evaluation_summary(self, hours: int = 720) -> Dict[str, Any]:
        """
        Get evaluation summary with confusion matrix.

        Args:
            hours: Number of hours to look back (default: 30 days)

        Returns:
            Dictionary with evaluation metrics
        """
        if not self.is_available:
            return {"error": "Database not available"}

        db = self._get_db_session()
        if not db:
            return {"error": "Could not get database session"}

        try:
            from db.metrics_repository import EvaluationRepository

            repo = EvaluationRepository(db)
            return repo.get_evaluation_summary(hours=hours)
        except Exception as e:
            logger.error(f"Failed to get evaluation summary: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    def cleanup_old_data(self):
        """Remove data older than retention period."""
        if not self.is_available:
            return

        db = self._get_db_session()
        if not db:
            return

        try:
            from db.models import (
                MetricSnapshot,
                AgentPerformance,
                LLMUsageRecord,
                LLMUsageSummary,
            )

            cutoff = datetime.utcnow() - timedelta(days=self.config.retention_days)

            # Delete old metric snapshots
            db.query(MetricSnapshot).filter(MetricSnapshot.timestamp < cutoff).delete()

            # Delete old agent performance records
            db.query(AgentPerformance).filter(AgentPerformance.timestamp < cutoff).delete()

            # Delete old LLM records
            db.query(LLMUsageRecord).filter(LLMUsageRecord.created_at < cutoff).delete()

            db.query(LLMUsageSummary).filter(LLMUsageSummary.timestamp < cutoff).delete()

            db.commit()
            logger.info(f"Cleaned up metrics data older than {cutoff}")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            db.rollback()
        finally:
            db.close()


# Global persistence instance
_persistence: Optional[MetricsPersistence] = None


def get_metrics_persistence() -> MetricsPersistence:
    """Get the global metrics persistence instance."""
    global _persistence
    if _persistence is None:
        config = PersistenceConfig.from_env()
        _persistence = MetricsPersistence(config)
    return _persistence


def start_metrics_persistence():
    """Start the metrics persistence scheduler."""
    persistence = get_metrics_persistence()
    persistence.start()


def stop_metrics_persistence():
    """Stop the metrics persistence scheduler."""
    global _persistence
    if _persistence:
        _persistence.stop()


# Convenience functions for event-based persistence


def persist_alert_received(entity_type: str, source: str):
    """Record an alert received event to database."""
    get_metrics_persistence().persist_alert_received(entity_type, source)


def persist_alert_processed(entity_type: str, severity: str, decision: str, processing_time: float):
    """Record an alert processed event to database."""
    get_metrics_persistence().persist_alert_processed(
        entity_type, severity, decision, processing_time
    )


def persist_agent_execution(agent_name: str, execution_time: float, success: bool = True):
    """Record an agent execution to database."""
    get_metrics_persistence().persist_agent_execution(agent_name, execution_time, success)


def persist_decision(
    entity_id: str,
    entity_type: str,
    action: str,
    risk_score: float,
    confidence: float,
    model_name: Optional[str] = None,
):
    """Record a fraud decision to database for later evaluation."""
    get_metrics_persistence().persist_decision(
        entity_id, entity_type, action, risk_score, confidence, model_name
    )
