"""
Metrics collection and evaluation for fraud detection system.

Provides comprehensive metrics for monitoring agent performance,
system health, and fraud detection accuracy.

Supports automatic persistence to PostgreSQL for historical tracking.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading

if TYPE_CHECKING:
    from observability.metrics_persistence import MetricsPersistence

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """A single metric value with timestamp."""

    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class HistogramBucket:
    """A histogram bucket."""

    le: float  # Less than or equal to
    count: int = 0


class Counter:
    """A monotonically increasing counter."""

    def __init__(self, name: str, description: str, labels: Optional[list[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, labels: Optional[dict[str, str]] = None):
        """Increment the counter."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] += value

    def get(self, labels: Optional[dict[str, str]] = None) -> float:
        """Get the current counter value for specific labels."""
        label_values = self._get_label_values(labels)
        return self._values.get(label_values, 0.0)

    def total(self) -> float:
        """Get the total sum across all label combinations."""
        with self._lock:
            return sum(self._values.values())

    def _get_label_values(self, labels: Optional[dict[str, str]]) -> tuple:
        if not labels:
            return ()
        return tuple(labels.get(name, "") for name in self.label_names)


class Gauge:
    """A gauge that can go up and down."""

    def __init__(self, name: str, description: str, labels: Optional[list[str]] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, labels: Optional[dict[str, str]] = None):
        """Set the gauge value."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] = value

    def inc(self, value: float = 1.0, labels: Optional[dict[str, str]] = None):
        """Increment the gauge."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] += value

    def dec(self, value: float = 1.0, labels: Optional[dict[str, str]] = None):
        """Decrement the gauge."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._values[label_values] -= value

    def get(self, labels: Optional[dict[str, str]] = None) -> float:
        """Get the current gauge value for specific labels."""
        label_values = self._get_label_values(labels)
        return self._values.get(label_values, 0.0)

    def total(self) -> float:
        """Get the total sum across all label combinations."""
        with self._lock:
            return sum(self._values.values())

    def _get_label_values(self, labels: Optional[dict[str, str]]) -> tuple:
        if not labels:
            return ()
        return tuple(labels.get(name, "") for name in self.label_names)


class Histogram:
    """A histogram for tracking distributions."""

    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
        buckets: Optional[list[float]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        self._counts: dict[tuple, dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self._sums: dict[tuple, float] = defaultdict(float)
        self._totals: dict[tuple, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, labels: Optional[dict[str, str]] = None):
        """Observe a value."""
        label_values = self._get_label_values(labels)
        with self._lock:
            self._sums[label_values] += value
            self._totals[label_values] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[label_values][bucket] += 1

    def get_stats(self, labels: Optional[dict[str, str]] = None) -> dict[str, Any]:
        """Get histogram statistics."""
        label_values = self._get_label_values(labels)
        total = self._totals.get(label_values, 0)
        sum_val = self._sums.get(label_values, 0.0)

        return {
            "count": total,
            "sum": sum_val,
            "mean": sum_val / total if total > 0 else 0.0,
            "buckets": dict(self._counts.get(label_values, {})),
        }

    def _get_label_values(self, labels: Optional[dict[str, str]]) -> tuple:
        if not labels:
            return ()
        return tuple(labels.get(name, "") for name in self.label_names)


class MetricsRegistry:
    """Central registry for all metrics."""

    def __init__(self):
        self._metrics: dict[str, Any] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, description: str, labels: Optional[list[str]] = None) -> Counter:
        """Create or get a counter."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Counter(name, description, labels)
            return self._metrics[name]

    def gauge(self, name: str, description: str, labels: Optional[list[str]] = None) -> Gauge:
        """Create or get a gauge."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Gauge(name, description, labels)
            return self._metrics[name]

    def histogram(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
        buckets: Optional[list[float]] = None,
    ) -> Histogram:
        """Create or get a histogram."""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = Histogram(name, description, labels, buckets)
            return self._metrics[name]

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        result = {}
        for name, metric in self._metrics.items():
            if isinstance(metric, Counter):
                result[name] = {"type": "counter", "values": dict(metric._values)}
            elif isinstance(metric, Gauge):
                result[name] = {"type": "gauge", "values": dict(metric._values)}
            elif isinstance(metric, Histogram):
                result[name] = {"type": "histogram", "stats": metric.get_stats()}
        return result


# Global metrics registry
_registry = MetricsRegistry()


def get_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    return _registry


# Pre-defined fraud detection metrics
class FraudMetrics:
    """
    Pre-defined metrics for fraud detection.

    Optionally integrates with MetricsPersistence for automatic
    database persistence of metrics.
    """

    def __init__(self, registry: Optional[MetricsRegistry] = None, enable_persistence: bool = True):
        self.registry = registry or get_registry()
        self._persistence: Optional["MetricsPersistence"] = None
        self._enable_persistence = enable_persistence

        # Alert processing metrics
        self.alerts_received = self.registry.counter(
            "fraud_alerts_received_total",
            "Total number of fraud alerts received",
            labels=["entity_type", "source"],
        )

        self.alerts_processed = self.registry.counter(
            "fraud_alerts_processed_total",
            "Total number of fraud alerts processed",
            labels=["entity_type", "severity", "decision"],
        )

        self.alert_processing_time = self.registry.histogram(
            "fraud_alert_processing_seconds",
            "Time to process fraud alerts",
            labels=["entity_type"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
        )

        # Agent metrics
        self.agent_execution_time = self.registry.histogram(
            "fraud_agent_execution_seconds",
            "Time for agent execution",
            labels=["agent_name"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
        )

        self.agent_errors = self.registry.counter(
            "fraud_agent_errors_total",
            "Total number of agent errors",
            labels=["agent_name", "error_type"],
        )

        # Decision metrics
        self.decisions_made = self.registry.counter(
            "fraud_decisions_total",
            "Total number of fraud decisions",
            labels=["action", "confidence_level"],
        )

        self.risk_scores = self.registry.histogram(
            "fraud_risk_score",
            "Distribution of risk scores",
            labels=["entity_type"],
            buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        )

        # Action metrics
        self.actions_executed = self.registry.counter(
            "fraud_actions_executed_total",
            "Total number of actions executed",
            labels=["action_type", "success"],
        )

        self.actions_rate_limited = self.registry.counter(
            "fraud_actions_rate_limited_total",
            "Total number of actions that were rate limited",
            labels=["action_type"],
        )

        # Human escalation metrics
        self.escalations = self.registry.counter(
            "fraud_escalations_total",
            "Total number of escalations to human review",
            labels=["reason"],
        )

        self.escalation_resolution_time = self.registry.histogram(
            "fraud_escalation_resolution_seconds",
            "Time to resolve human escalations",
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400],
        )

        # Tool metrics
        self.tool_calls = self.registry.counter(
            "fraud_tool_calls_total",
            "Total number of external tool calls",
            labels=["tool_name", "success"],
        )

        self.tool_latency = self.registry.histogram(
            "fraud_tool_latency_seconds",
            "Latency of external tool calls",
            labels=["tool_name"],
            buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        # LLM metrics (if using LLM for reasoning)
        self.llm_calls = self.registry.counter(
            "fraud_llm_calls_total", "Total number of LLM calls", labels=["model", "success"]
        )

        self.llm_tokens = self.registry.counter(
            "fraud_llm_tokens_total",
            "Total tokens used by LLM",
            labels=["model", "direction"],  # direction: input/output
        )

        self.llm_latency = self.registry.histogram(
            "fraud_llm_latency_seconds",
            "Latency of LLM calls",
            labels=["model"],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )

        # System health gauges
        self.active_workflows = self.registry.gauge(
            "fraud_active_workflows", "Number of currently active workflows"
        )

        self.pending_escalations = self.registry.gauge(
            "fraud_pending_escalations", "Number of pending human escalations"
        )

        # Initialize persistence if enabled
        if self._enable_persistence:
            self._init_persistence()

    def _init_persistence(self):
        """Initialize the persistence layer."""
        try:
            from observability.metrics_persistence import get_metrics_persistence

            self._persistence = get_metrics_persistence()
            logger.info("FraudMetrics: Persistence layer initialized")
        except ImportError:
            logger.debug("FraudMetrics: Persistence module not available")
        except Exception as e:
            logger.warning(f"FraudMetrics: Failed to initialize persistence - {e}")

    @property
    def persistence(self) -> Optional["MetricsPersistence"]:
        """Get the persistence layer instance."""
        return self._persistence

    def enable_persistence(self, persistence: Optional["MetricsPersistence"] = None):
        """
        Enable persistence for this metrics instance.

        Args:
            persistence: Optional custom persistence instance
        """
        if persistence:
            self._persistence = persistence
        else:
            self._init_persistence()
        self._enable_persistence = True

    def disable_persistence(self):
        """Disable persistence for this metrics instance."""
        self._enable_persistence = False

    def record_alert_received(self, entity_type: str, source: str):
        """Record that an alert was received."""
        self.alerts_received.inc(labels={"entity_type": entity_type, "source": source})

        # Persist to database if enabled
        if self._persistence and self._enable_persistence:
            try:
                self._persistence.persist_alert_received(entity_type, source)
            except Exception as e:
                logger.debug(f"Failed to persist alert received: {e}")

    def record_alert_processed(
        self, entity_type: str, severity: str, decision: str, processing_time: float
    ):
        """Record that an alert was processed."""
        self.alerts_processed.inc(
            labels={"entity_type": entity_type, "severity": severity, "decision": decision}
        )
        self.alert_processing_time.observe(processing_time, labels={"entity_type": entity_type})

        # Persist to database if enabled
        if self._persistence and self._enable_persistence:
            try:
                self._persistence.persist_alert_processed(
                    entity_type, severity, decision, processing_time
                )
            except Exception as e:
                logger.debug(f"Failed to persist alert processed: {e}")

    def record_agent_execution(
        self, agent_name: str, execution_time: float, error: Optional[str] = None
    ):
        """Record agent execution."""
        self.agent_execution_time.observe(execution_time, labels={"agent_name": agent_name})
        if error:
            self.agent_errors.inc(labels={"agent_name": agent_name, "error_type": error})

        # Persist to database if enabled
        if self._persistence and self._enable_persistence:
            try:
                self._persistence.persist_agent_execution(
                    agent_name, execution_time, success=(error is None)
                )
            except Exception as e:
                logger.debug(f"Failed to persist agent execution: {e}")

    def record_decision(
        self,
        action: str,
        confidence: float,
        risk_score: float,
        entity_type: str,
        entity_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        """Record a fraud decision."""
        confidence_level = "high" if confidence >= 0.7 else "medium" if confidence >= 0.4 else "low"
        self.decisions_made.inc(labels={"action": action, "confidence_level": confidence_level})
        self.risk_scores.observe(risk_score, labels={"entity_type": entity_type})

        # Persist to database if enabled (for evaluation tracking)
        if self._persistence and self._enable_persistence and entity_id:
            try:
                self._persistence.persist_decision(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    action=action,
                    risk_score=risk_score,
                    confidence=confidence,
                    model_name=model_name,
                )
            except Exception as e:
                logger.debug(f"Failed to persist decision: {e}")

    def record_action(self, action_type: str, success: bool):
        """Record an action execution."""
        self.actions_executed.inc(labels={"action_type": action_type, "success": str(success)})

    def record_rate_limit(self, action_type: str):
        """Record a rate-limited action."""
        self.actions_rate_limited.inc(labels={"action_type": action_type})

    def record_escalation(self, reason: str):
        """Record an escalation to human review."""
        self.escalations.inc(labels={"reason": reason})
        self.pending_escalations.inc()

    def record_escalation_resolved(self, resolution_time: float):
        """Record that an escalation was resolved."""
        self.escalation_resolution_time.observe(resolution_time)
        self.pending_escalations.dec()

    def record_tool_call(self, tool_name: str, success: bool, latency: float):
        """Record an external tool call."""
        self.tool_calls.inc(labels={"tool_name": tool_name, "success": str(success)})
        self.tool_latency.observe(latency, labels={"tool_name": tool_name})

    def record_llm_call(
        self,
        model: str,
        success: bool,
        latency: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        """Record an LLM call."""
        self.llm_calls.inc(labels={"model": model, "success": str(success)})
        self.llm_latency.observe(latency, labels={"model": model})
        if input_tokens:
            self.llm_tokens.inc(input_tokens, labels={"model": model, "direction": "input"})
        if output_tokens:
            self.llm_tokens.inc(output_tokens, labels={"model": model, "direction": "output"})


# Global metrics instance
_fraud_metrics: Optional[FraudMetrics] = None


def get_fraud_metrics() -> FraudMetrics:
    """Get the global fraud metrics instance."""
    global _fraud_metrics
    if _fraud_metrics is None:
        _fraud_metrics = FraudMetrics()
    return _fraud_metrics


def export_prometheus(registry: Optional[MetricsRegistry] = None) -> str:
    """
    Export all metrics in Prometheus text format.

    This format can be scraped by Prometheus server or compatible systems.
    See: https://prometheus.io/docs/instrumenting/exposition_formats/

    Returns:
        str: Metrics in Prometheus exposition format
    """
    reg = registry or get_registry()
    lines = []

    for name, metric in reg._metrics.items():
        if isinstance(metric, Counter):
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} counter")

            if not metric._values:
                lines.append(f"{name} 0")
            else:
                for label_values, value in metric._values.items():
                    if label_values:
                        labels_str = ",".join(
                            f'{label}="{val}"'
                            for label, val in zip(metric.label_names, label_values)
                        )
                        lines.append(f"{name}{{{labels_str}}} {value}")
                    else:
                        lines.append(f"{name} {value}")

        elif isinstance(metric, Gauge):
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} gauge")

            if not metric._values:
                lines.append(f"{name} 0")
            else:
                for label_values, value in metric._values.items():
                    if label_values:
                        labels_str = ",".join(
                            f'{label}="{val}"'
                            for label, val in zip(metric.label_names, label_values)
                        )
                        lines.append(f"{name}{{{labels_str}}} {value}")
                    else:
                        lines.append(f"{name} {value}")

        elif isinstance(metric, Histogram):
            lines.append(f"# HELP {name} {metric.description}")
            lines.append(f"# TYPE {name} histogram")

            for label_values in metric._totals.keys():
                base_labels = ""
                if label_values:
                    base_labels = ",".join(
                        f'{label}="{val}"' for label, val in zip(metric.label_names, label_values)
                    )

                # Export bucket counts
                cumulative = 0
                for bucket in metric.buckets:
                    cumulative += metric._counts.get(label_values, {}).get(bucket, 0)
                    if base_labels:
                        lines.append(f'{name}_bucket{{{base_labels},le="{bucket}"}} {cumulative}')
                    else:
                        lines.append(f'{name}_bucket{{le="{bucket}"}} {cumulative}')

                # +Inf bucket
                total_count = metric._totals.get(label_values, 0)
                if base_labels:
                    lines.append(f'{name}_bucket{{{base_labels},le="+Inf"}} {total_count}')
                    lines.append(f"{name}_sum{{{base_labels}}} {metric._sums.get(label_values, 0)}")
                    lines.append(f"{name}_count{{{base_labels}}} {total_count}")
                else:
                    lines.append(f'{name}_bucket{{le="+Inf"}} {total_count}')
                    lines.append(f"{name}_sum {metric._sums.get(label_values, 0)}")
                    lines.append(f"{name}_count {total_count}")

            # If no data yet, output zeros
            if not metric._totals:
                for bucket in metric.buckets:
                    lines.append(f'{name}_bucket{{le="{bucket}"}} 0')
                lines.append(f'{name}_bucket{{le="+Inf"}} 0')
                lines.append(f"{name}_sum 0")
                lines.append(f"{name}_count 0")

    lines.append("")  # Trailing newline
    return "\n".join(lines)
