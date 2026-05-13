"""
Observability package for fraud detection system.

Provides tracing, metrics, evaluation, logging, and persistence capabilities.
"""

from observability.tracing import (
    Tracer,
    Trace,
    Span,
    SpanStatus,
    SpanKind,
    TracingContext,
    get_tracer,
    set_tracer,
    trace_agent,
    trace_tool,
    trace_llm_call,
)

from observability.metrics import (
    MetricsRegistry,
    Counter,
    Gauge,
    Histogram,
    FraudMetrics,
    get_registry,
    get_fraud_metrics,
)

from observability.evaluation import (
    EvaluationStore,
    EvaluationRecord,
    EvaluationOutcome,
    ConfusionMatrix,
    AgentPerformanceMetrics,
    FeedbackLoop,
    get_evaluation_store,
    get_feedback_loop,
)

from observability.logging import (
    setup_logging,
    get_logger,
    get_audit_logger,
    AuditLogger,
    ContextLogger,
)

from observability.metrics_persistence import (
    MetricsPersistence,
    PersistenceConfig,
    PersistenceInterval,
    get_metrics_persistence,
    start_metrics_persistence,
    stop_metrics_persistence,
    persist_alert_received,
    persist_alert_processed,
    persist_agent_execution,
    persist_decision,
)

__all__ = [
    # Tracing
    "Tracer",
    "Trace",
    "Span",
    "SpanStatus",
    "SpanKind",
    "TracingContext",
    "get_tracer",
    "set_tracer",
    "trace_agent",
    "trace_tool",
    "trace_llm_call",
    # Metrics
    "MetricsRegistry",
    "Counter",
    "Gauge",
    "Histogram",
    "FraudMetrics",
    "get_registry",
    "get_fraud_metrics",
    # Evaluation
    "EvaluationStore",
    "EvaluationRecord",
    "EvaluationOutcome",
    "ConfusionMatrix",
    "AgentPerformanceMetrics",
    "FeedbackLoop",
    "get_evaluation_store",
    "get_feedback_loop",
    # Logging
    "setup_logging",
    "get_logger",
    "get_audit_logger",
    "AuditLogger",
    "ContextLogger",
    # Persistence
    "MetricsPersistence",
    "PersistenceConfig",
    "PersistenceInterval",
    "get_metrics_persistence",
    "start_metrics_persistence",
    "stop_metrics_persistence",
    "persist_alert_received",
    "persist_alert_processed",
    "persist_agent_execution",
    "persist_decision",
]
