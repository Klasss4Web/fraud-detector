"""
Observability API endpoints for monitoring and evaluation.
"""

from typing import Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from src.observability import (
    get_registry,
    get_fraud_metrics,
    get_evaluation_store,
    get_feedback_loop,
    EvaluationOutcome,
)
from observability.metrics import export_prometheus
from observability.llm_tracking import get_llm_tracker

router = APIRouter(prefix="/observability", tags=["Observability"])


# ============== Request/Response Models ==============


class MetricsResponse(BaseModel):
    """Response containing all metrics."""

    metrics: dict[str, Any]


class EvaluationSummaryResponse(BaseModel):
    """Response containing evaluation summary."""

    timestamp: str
    total_evaluated: int
    overall_metrics: dict[str, Any]
    metrics_by_entity_type: dict[str, dict[str, Any]]
    agent_performance: dict[str, dict[str, Any]]
    negative_exemplar_count: int


class HumanOverrideRequest(BaseModel):
    """Request to record a human override."""

    alert_id: str = Field(..., description="Alert ID that was overridden")
    entity_type: str = Field(..., description="Type of entity")
    agent_decision: str = Field(..., description="Original agent decision")
    human_decision: str = Field(..., description="Human analyst decision")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score from agent")
    confidence: float = Field(..., ge=0, le=1, description="Confidence from agent")
    analyst_id: str = Field(..., description="ID of the human analyst")
    reason: str = Field("", description="Reason for override")


class ChargebackRequest(BaseModel):
    """Request to record a chargeback."""

    alert_id: str = Field(..., description="Alert ID associated with chargeback")
    entity_type: str = Field(..., description="Type of entity")
    original_decision: str = Field(..., description="Original decision made")
    risk_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)


class UserConfirmationRequest(BaseModel):
    """Request to record user confirmation."""

    alert_id: str = Field(..., description="Alert ID")
    entity_type: str = Field(..., description="Type of entity")
    original_decision: str = Field(..., description="Original decision made")
    risk_score: float = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)
    was_legitimate: bool = Field(..., description="Whether user confirmed activity as legitimate")


class FeedbackResponse(BaseModel):
    """Response for feedback submission."""

    success: bool
    message: str
    outcome: Optional[str] = None


class ImprovementSuggestion(BaseModel):
    """An improvement suggestion from the feedback loop."""

    type: str
    issue: str
    details: str
    suggestion: str


class ImprovementSuggestionsResponse(BaseModel):
    """Response containing improvement suggestions."""

    suggestions: list[ImprovementSuggestion]


# ============== Endpoints ==============


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Get all collected metrics.

    Returns current values for all counters, gauges, and histograms.
    """
    registry = get_registry()
    return MetricsResponse(metrics=registry.get_all_metrics())


@router.get(
    "/metrics/prometheus",
    response_class=PlainTextResponse,
    summary="Prometheus metrics endpoint",
)
async def get_prometheus_metrics():
    """
    Export metrics in Prometheus text format.

    This endpoint can be scraped by Prometheus server or compatible
    monitoring systems (Grafana Agent, Victoria Metrics, etc.).

    Configure Prometheus to scrape this endpoint:
    ```yaml
    scrape_configs:
      - job_name: 'fraud-detection'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/api/v1/observability/metrics/prometheus'
    ```
    """
    return PlainTextResponse(
        content=export_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/metrics/fraud", response_model=dict[str, Any])
async def get_fraud_specific_metrics():
    """
    Get fraud-specific metrics summary.
    """
    metrics = get_fraud_metrics()

    return {
        "alerts": {
            "received": metrics.alerts_received.total(),
            "processed": metrics.alerts_processed.total(),
        },
        "decisions": {
            "total": metrics.decisions_made.total(),
        },
        "actions": {
            "executed": metrics.actions_executed.total(),
            "rate_limited": metrics.actions_rate_limited.total(),
        },
        "escalations": {
            "total": metrics.escalations.total(),
            "pending": metrics.pending_escalations.total(),
        },
        "system": {
            "active_workflows": metrics.active_workflows.total(),
        },
    }


@router.get("/evaluation/summary", response_model=EvaluationSummaryResponse)
async def get_evaluation_summary():
    """
    Get evaluation summary including confusion matrix and agent performance.
    """
    store = get_evaluation_store()
    report = store.get_summary_report()

    return EvaluationSummaryResponse(**report)


@router.get("/evaluation/confusion-matrix")
async def get_confusion_matrix(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
):
    """
    Get confusion matrix for fraud detection accuracy.
    """
    store = get_evaluation_store()
    matrix = store.get_confusion_matrix(entity_type)

    return matrix.to_dict()


@router.get("/evaluation/agent-performance")
async def get_agent_performance(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
):
    """
    Get performance metrics for agents.
    """
    store = get_evaluation_store()
    metrics = store.get_agent_metrics(agent_name)

    return {name: m.to_dict() for name, m in metrics.items()}


@router.post("/feedback/human-override", response_model=FeedbackResponse)
async def record_human_override(request: HumanOverrideRequest):
    """
    Record when a human analyst overrides an agent decision.

    This feedback is used to improve future decision-making.
    """
    feedback_loop = get_feedback_loop()

    record = feedback_loop.record_human_override(
        alert_id=request.alert_id,
        entity_type=request.entity_type,
        agent_decision=request.agent_decision,
        human_decision=request.human_decision,
        risk_score=request.risk_score,
        confidence=request.confidence,
        reason=request.reason,
    )

    return FeedbackResponse(
        success=True,
        message=f"Human override recorded for alert {request.alert_id}",
        outcome=record.actual_outcome.value if record.actual_outcome else None,
    )


@router.post("/feedback/chargeback", response_model=FeedbackResponse)
async def record_chargeback(request: ChargebackRequest):
    """
    Record a chargeback, indicating fraud was missed.
    """
    feedback_loop = get_feedback_loop()

    record = feedback_loop.record_chargeback(
        alert_id=request.alert_id,
        entity_type=request.entity_type,
        original_decision=request.original_decision,
        risk_score=request.risk_score,
        confidence=request.confidence,
    )

    return FeedbackResponse(
        success=True,
        message=f"Chargeback recorded for alert {request.alert_id}",
        outcome=record.actual_outcome.value if record.actual_outcome else None,
    )


@router.post("/feedback/user-confirmation", response_model=FeedbackResponse)
async def record_user_confirmation(request: UserConfirmationRequest):
    """
    Record user confirmation of whether activity was legitimate.
    """
    feedback_loop = get_feedback_loop()

    record = feedback_loop.record_user_confirmation(
        alert_id=request.alert_id,
        entity_type=request.entity_type,
        original_decision=request.original_decision,
        risk_score=request.risk_score,
        confidence=request.confidence,
        was_legitimate=request.was_legitimate,
    )

    return FeedbackResponse(
        success=True,
        message=f"User confirmation recorded for alert {request.alert_id}",
        outcome=record.actual_outcome.value if record.actual_outcome else None,
    )


@router.get("/feedback/negative-exemplars")
async def get_negative_exemplars(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of exemplars"),
):
    """
    Get recent negative exemplars (incorrect decisions) for analysis.
    """
    store = get_evaluation_store()
    exemplars = store.get_negative_exemplars(limit)

    return {
        "count": len(exemplars),
        "exemplars": exemplars,
    }


@router.get("/feedback/improvement-suggestions", response_model=ImprovementSuggestionsResponse)
async def get_improvement_suggestions():
    """
    Get AI-generated suggestions for improving the system based on feedback.
    """
    feedback_loop = get_feedback_loop()
    suggestions = feedback_loop.get_improvement_suggestions()

    return ImprovementSuggestionsResponse(
        suggestions=[ImprovementSuggestion(**s) for s in suggestions]
    )


# ============== LLM Usage Models ==============


class LLMTokensByOperation(BaseModel):
    """Token usage breakdown by operation."""

    operation: str
    calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: float
    avg_tokens_per_call: float
    avg_latency_ms: float


class LLMTokensByModel(BaseModel):
    """Token usage breakdown by model."""

    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: float
    avg_tokens_per_call: float


class LLMTokensByAgent(BaseModel):
    """Token usage breakdown by agent."""

    agent_name: str
    calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: float
    avg_tokens_per_call: float


class LLMUsageSummaryResponse(BaseModel):
    """Comprehensive LLM usage summary."""

    period_hours: int
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    tokens: dict[str, Any]
    cost: dict[str, Any]
    latency: dict[str, Any]
    by_operation: List[LLMTokensByOperation]
    by_model: List[LLMTokensByModel]
    by_agent: List[LLMTokensByAgent]


class LLMRecentCallResponse(BaseModel):
    """Recent LLM call record."""

    call_id: str
    model: str
    timestamp: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: float
    latency_ms: float
    success: bool
    agent_name: str
    operation: str
    entity_id: Optional[str] = None
    error: Optional[str] = None


class LLMHourlyStats(BaseModel):
    """Hourly LLM usage statistics."""

    hour: str
    calls: int
    tokens: int
    cost: float


class LLMOperationDetail(BaseModel):
    """Detailed metrics for a specific operation."""

    operation: str
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    avg_input_tokens: float
    avg_output_tokens: float
    avg_tokens_per_call: float
    avg_cost_per_call: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    models_used: List[str]
    agents_using: List[str]


# ============== LLM Usage Endpoints ==============


@router.get("/llm/usage", response_model=LLMUsageSummaryResponse)
async def get_llm_usage_summary(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
):
    """
    Get comprehensive LLM usage statistics.

    Includes token usage, costs, and breakdowns by operation, model, and agent.
    """
    tracker = get_llm_tracker()
    stats = tracker.get_stats(hours=hours)

    # Transform by_operation to list format with detailed metrics
    by_operation = []
    for op_name, op_data in stats.get("by_operation", {}).items():
        calls = op_data.get("calls", 0)
        tokens = op_data.get("tokens", 0)
        by_operation.append(
            LLMTokensByOperation(
                operation=op_name,
                calls=calls,
                input_tokens=0,  # Will be calculated from detailed stats
                output_tokens=0,
                total_tokens=tokens,
                total_cost=op_data.get("cost", 0.0),
                avg_tokens_per_call=round(tokens / calls, 1) if calls > 0 else 0,
                avg_latency_ms=op_data.get("avg_latency_ms", 0.0),
            )
        )

    # Transform by_model to list format
    by_model = []
    for model_name, model_data in stats.get("by_model", {}).items():
        calls = model_data.get("calls", 0)
        tokens = model_data.get("tokens", 0)
        by_model.append(
            LLMTokensByModel(
                model=model_name,
                calls=calls,
                input_tokens=0,
                output_tokens=0,
                total_tokens=tokens,
                total_cost=model_data.get("cost", 0.0),
                avg_tokens_per_call=round(tokens / calls, 1) if calls > 0 else 0,
            )
        )

    # Transform by_agent to list format
    by_agent = []
    for agent_name, agent_data in stats.get("by_agent", {}).items():
        calls = agent_data.get("calls", 0)
        tokens = agent_data.get("tokens", 0)
        by_agent.append(
            LLMTokensByAgent(
                agent_name=agent_name,
                calls=calls,
                input_tokens=0,
                output_tokens=0,
                total_tokens=tokens,
                total_cost=agent_data.get("cost", 0.0),
                avg_tokens_per_call=round(tokens / calls, 1) if calls > 0 else 0,
            )
        )

    # Sort by total tokens descending
    by_operation.sort(key=lambda x: x.total_tokens, reverse=True)
    by_model.sort(key=lambda x: x.total_tokens, reverse=True)
    by_agent.sort(key=lambda x: x.total_tokens, reverse=True)

    return LLMUsageSummaryResponse(
        period_hours=hours,
        total_calls=stats.get("total_calls", 0),
        successful_calls=stats.get("successful_calls", 0),
        failed_calls=stats.get("failed_calls", 0),
        success_rate=stats.get("success_rate", 0.0),
        tokens=stats.get("tokens", {}),
        cost=stats.get("cost", {}),
        latency=stats.get("latency", {}),
        by_operation=by_operation,
        by_model=by_model,
        by_agent=by_agent,
    )


@router.get("/llm/usage/by-operation", response_model=List[LLMOperationDetail])
async def get_llm_usage_by_operation(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
    operation: Optional[str] = Query(None, description="Filter by specific operation"),
):
    """
    Get detailed LLM token usage broken down by operation.

    Operations include: analyze, recommend, investigate, triage, decide, etc.
    """
    tracker = get_llm_tracker()

    # Get recent calls for detailed analysis
    recent_calls = tracker.get_recent_calls(limit=1000)

    # Filter by time if needed
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    # Group by operation
    operation_stats: dict[str, dict] = {}

    for call in recent_calls:
        # Parse timestamp
        try:
            call_time = datetime.fromisoformat(call["timestamp"].replace("Z", "+00:00"))
            if call_time.tzinfo:
                call_time = call_time.replace(tzinfo=None)
        except:
            continue

        if call_time < cutoff:
            continue

        op_name = call.get("operation", "unknown")

        # Filter by operation if specified
        if operation and op_name != operation:
            continue

        if op_name not in operation_stats:
            operation_stats[op_name] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_latency_ms": 0.0,
                "min_latency_ms": float("inf"),
                "max_latency_ms": 0.0,
                "models": set(),
                "agents": set(),
            }

        stats = operation_stats[op_name]
        stats["total_calls"] += 1

        if call.get("success", True):
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1

        stats["total_input_tokens"] += call.get("input_tokens", 0)
        stats["total_output_tokens"] += call.get("output_tokens", 0)
        stats["total_tokens"] += call.get("total_tokens", 0)
        stats["total_cost"] += call.get("total_cost", 0.0)

        latency = call.get("latency_ms", 0.0)
        stats["total_latency_ms"] += latency
        stats["min_latency_ms"] = min(stats["min_latency_ms"], latency)
        stats["max_latency_ms"] = max(stats["max_latency_ms"], latency)

        stats["models"].add(call.get("model", "unknown"))
        stats["agents"].add(call.get("agent_name", "unknown"))

    # Convert to response format
    result = []
    for op_name, stats in operation_stats.items():
        total_calls = stats["total_calls"]
        result.append(
            LLMOperationDetail(
                operation=op_name,
                total_calls=total_calls,
                successful_calls=stats["successful_calls"],
                failed_calls=stats["failed_calls"],
                success_rate=round(stats["successful_calls"] / total_calls, 4)
                if total_calls > 0
                else 0,
                total_input_tokens=stats["total_input_tokens"],
                total_output_tokens=stats["total_output_tokens"],
                total_tokens=stats["total_tokens"],
                total_cost=round(stats["total_cost"], 4),
                avg_input_tokens=round(stats["total_input_tokens"] / total_calls, 1)
                if total_calls > 0
                else 0,
                avg_output_tokens=round(stats["total_output_tokens"] / total_calls, 1)
                if total_calls > 0
                else 0,
                avg_tokens_per_call=round(stats["total_tokens"] / total_calls, 1)
                if total_calls > 0
                else 0,
                avg_cost_per_call=round(stats["total_cost"] / total_calls, 6)
                if total_calls > 0
                else 0,
                avg_latency_ms=round(stats["total_latency_ms"] / total_calls, 2)
                if total_calls > 0
                else 0,
                min_latency_ms=round(stats["min_latency_ms"], 2)
                if stats["min_latency_ms"] != float("inf")
                else 0,
                max_latency_ms=round(stats["max_latency_ms"], 2),
                models_used=sorted(list(stats["models"])),
                agents_using=sorted(list(stats["agents"])),
            )
        )

    # Sort by total tokens descending
    result.sort(key=lambda x: x.total_tokens, reverse=True)

    return result


@router.get("/llm/usage/recent", response_model=List[LLMRecentCallResponse])
async def get_recent_llm_calls(
    limit: int = Query(50, ge=1, le=500, description="Number of recent calls to return"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    agent: Optional[str] = Query(None, description="Filter by agent name"),
    model: Optional[str] = Query(None, description="Filter by model"),
    success_only: bool = Query(False, description="Only show successful calls"),
):
    """
    Get recent LLM API calls with detailed information.

    Useful for debugging and monitoring individual LLM interactions.
    """
    tracker = get_llm_tracker()
    calls = tracker.get_recent_calls(limit=limit * 2)  # Get extra for filtering

    # Apply filters
    filtered_calls = []
    for call in calls:
        if operation and call.get("operation") != operation:
            continue
        if agent and call.get("agent_name") != agent:
            continue
        if model and call.get("model") != model:
            continue
        if success_only and not call.get("success", True):
            continue

        filtered_calls.append(
            LLMRecentCallResponse(
                call_id=call.get("call_id", ""),
                model=call.get("model", ""),
                timestamp=call.get("timestamp", ""),
                input_tokens=call.get("input_tokens", 0),
                output_tokens=call.get("output_tokens", 0),
                total_tokens=call.get("total_tokens", 0),
                total_cost=call.get("total_cost", 0.0),
                latency_ms=call.get("latency_ms", 0.0),
                success=call.get("success", True),
                agent_name=call.get("agent_name", ""),
                operation=call.get("operation", ""),
                entity_id=call.get("entity_id"),
                error=call.get("error"),
            )
        )

        if len(filtered_calls) >= limit:
            break

    return filtered_calls


@router.get("/llm/usage/hourly", response_model=List[LLMHourlyStats])
async def get_hourly_llm_stats(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
):
    """
    Get hourly breakdown of LLM usage.

    Useful for identifying usage patterns and peak hours.
    """
    tracker = get_llm_tracker()
    hourly = tracker.get_hourly_stats(hours=hours)

    return [LLMHourlyStats(**h) for h in hourly]


@router.get("/llm/usage/cost-breakdown")
async def get_llm_cost_breakdown(
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
):
    """
    Get LLM cost breakdown by model, operation, and agent.

    Helps identify cost optimization opportunities.
    """
    tracker = get_llm_tracker()
    stats = tracker.get_stats(hours=hours)

    # Calculate cost percentages
    total_cost = stats.get("cost", {}).get("total_usd", 0.0)

    by_model = []
    for model, data in stats.get("by_model", {}).items():
        cost = data.get("cost", 0.0)
        by_model.append(
            {
                "model": model,
                "cost": round(cost, 4),
                "percentage": round((cost / total_cost * 100) if total_cost > 0 else 0, 2),
                "calls": data.get("calls", 0),
                "tokens": data.get("tokens", 0),
            }
        )

    by_operation = []
    for op, data in stats.get("by_operation", {}).items():
        cost = data.get("cost", 0.0)
        by_operation.append(
            {
                "operation": op,
                "cost": round(cost, 4),
                "percentage": round((cost / total_cost * 100) if total_cost > 0 else 0, 2),
                "calls": data.get("calls", 0),
                "tokens": data.get("tokens", 0),
            }
        )

    by_agent = []
    for agent, data in stats.get("by_agent", {}).items():
        cost = data.get("cost", 0.0)
        by_agent.append(
            {
                "agent": agent,
                "cost": round(cost, 4),
                "percentage": round((cost / total_cost * 100) if total_cost > 0 else 0, 2),
                "calls": data.get("calls", 0),
                "tokens": data.get("tokens", 0),
            }
        )

    # Sort by cost descending
    by_model.sort(key=lambda x: x["cost"], reverse=True)
    by_operation.sort(key=lambda x: x["cost"], reverse=True)
    by_agent.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "period_hours": hours,
        "total_cost_usd": round(total_cost, 4),
        "total_calls": stats.get("total_calls", 0),
        "total_tokens": stats.get("tokens", {}).get("total", 0),
        "by_model": by_model,
        "by_operation": by_operation,
        "by_agent": by_agent,
    }


@router.get("/llm/operations")
async def list_llm_operations():
    """
    List all unique operations that have made LLM calls.

    Useful for filtering and understanding what operations use LLM.
    """
    tracker = get_llm_tracker()
    stats = tracker.get_stats(hours=720)  # Last 30 days

    operations = []
    for op_name, op_data in stats.get("by_operation", {}).items():
        operations.append(
            {
                "operation": op_name,
                "total_calls": op_data.get("calls", 0),
                "total_tokens": op_data.get("tokens", 0),
                "total_cost": round(op_data.get("cost", 0.0), 4),
            }
        )

    operations.sort(key=lambda x: x["total_calls"], reverse=True)

    return {
        "operations": operations,
        "total_operations": len(operations),
    }
