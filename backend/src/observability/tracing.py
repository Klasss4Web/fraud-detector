"""
Tracing system for fraud detection workflow.

Provides distributed tracing capabilities to track the flow of
alerts through the multi-agent system with full observability.
"""

import uuid
import time
import logging
import json
from datetime import datetime
from typing import Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


class SpanStatus(Enum):
    """Status of a trace span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class SpanKind(Enum):
    """Type of span in the trace."""

    INTERNAL = "internal"
    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    EXTERNAL_API = "external_api"
    DATABASE = "database"


@dataclass
class SpanEvent:
    """An event that occurred during a span."""

    name: str
    timestamp: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A single span in a trace representing a unit of work."""

    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    def add_event(self, name: str, attributes: Optional[dict] = None):
        """Add an event to the span."""
        self.events.append(
            SpanEvent(
                name=name,
                timestamp=datetime.utcnow().isoformat(),
                attributes=attributes or {},
            )
        )

    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value

    def set_status(self, status: SpanStatus, message: Optional[str] = None):
        """Set the span status."""
        self.status = status
        if message:
            self.error_message = message

    def end(self, status: Optional[SpanStatus] = None):
        """End the span."""
        self.end_time = time.time()
        if status:
            self.status = status
        elif self.status == SpanStatus.UNSET:
            self.status = SpanStatus.OK

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dictionary for serialization."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [asdict(e) for e in self.events],
            "error_message": self.error_message,
        }


@dataclass
class Trace:
    """A complete trace representing the full lifecycle of an alert."""

    trace_id: str
    alert_id: str
    start_time: float
    end_time: Optional[float] = None
    spans: list[Span] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Get total trace duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    @property
    def span_count(self) -> int:
        """Get total number of spans."""
        return len(self.spans)

    @property
    def error_count(self) -> int:
        """Get number of spans with errors."""
        return sum(1 for s in self.spans if s.status == SpanStatus.ERROR)

    def add_span(self, span: Span):
        """Add a span to the trace."""
        self.spans.append(span)

    def end(self):
        """End the trace."""
        self.end_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "alert_id": self.alert_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
            "duration_ms": self.duration_ms,
            "span_count": self.span_count,
            "error_count": self.error_count,
            "spans": [s.to_dict() for s in self.spans],
            "metadata": self.metadata,
        }

    def get_timeline(self) -> list[dict[str, Any]]:
        """Get a timeline view of all spans."""
        return sorted(
            [
                {
                    "name": s.name,
                    "start": s.start_time,
                    "duration_ms": s.duration_ms,
                    "status": s.status.value,
                }
                for s in self.spans
            ],
            key=lambda x: x["start"],
        )


class TracingContext:
    """Thread-local context for tracing."""

    _current_trace: Optional[Trace] = None
    _current_span: Optional[Span] = None
    _span_stack: list[Span] = []

    @classmethod
    def get_current_trace(cls) -> Optional[Trace]:
        return cls._current_trace

    @classmethod
    def get_current_span(cls) -> Optional[Span]:
        return cls._current_span

    @classmethod
    def set_current_trace(cls, trace: Optional[Trace]):
        cls._current_trace = trace

    @classmethod
    def set_current_span(cls, span: Optional[Span]):
        cls._current_span = span

    @classmethod
    def push_span(cls, span: Span):
        if cls._current_span:
            cls._span_stack.append(cls._current_span)
        cls._current_span = span

    @classmethod
    def pop_span(cls) -> Optional[Span]:
        current = cls._current_span
        if cls._span_stack:
            cls._current_span = cls._span_stack.pop()
        else:
            cls._current_span = None
        return current

    @classmethod
    def clear(cls):
        cls._current_trace = None
        cls._current_span = None
        cls._span_stack = []


class Tracer:
    """
    Main tracer class for creating and managing traces.
    """

    def __init__(self, service_name: str = "fraud-detection"):
        self.service_name = service_name
        self._traces: dict[str, Trace] = {}
        self._exporters: list[Callable[[Trace], None]] = []

    def add_exporter(self, exporter: Callable[[Trace], None]):
        """Add a trace exporter (e.g., to send to observability platform)."""
        self._exporters.append(exporter)

    def start_trace(self, alert_id: str, metadata: Optional[dict] = None) -> Trace:
        """Start a new trace for an alert."""
        trace_id = str(uuid.uuid4())
        trace = Trace(
            trace_id=trace_id,
            alert_id=alert_id,
            start_time=time.time(),
            metadata=metadata or {},
        )
        trace.metadata["service"] = self.service_name
        self._traces[trace_id] = trace
        TracingContext.set_current_trace(trace)

        logger.debug(f"Started trace {trace_id} for alert {alert_id}")
        return trace

    def end_trace(self, trace: Trace):
        """End a trace and export it."""
        trace.end()
        TracingContext.clear()

        # Export to all registered exporters
        for exporter in self._exporters:
            try:
                exporter(trace)
            except Exception as e:
                logger.error(f"Failed to export trace: {e}")

        logger.debug(f"Ended trace {trace.trace_id}, duration: {trace.duration_ms:.2f}ms")

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[dict] = None,
    ) -> Span:
        """Start a new span."""
        trace = TracingContext.get_current_trace()
        parent = TracingContext.get_current_span()

        span = Span(
            span_id=str(uuid.uuid4())[:16],
            trace_id=trace.trace_id if trace else str(uuid.uuid4()),
            parent_span_id=parent.span_id if parent else None,
            name=name,
            kind=kind,
            start_time=time.time(),
            attributes=attributes or {},
        )

        if trace:
            trace.add_span(span)

        TracingContext.push_span(span)
        logger.debug(f"Started span {span.name} ({span.span_id})")

        return span

    def end_span(self, span: Span, status: Optional[SpanStatus] = None):
        """End a span."""
        span.end(status)
        TracingContext.pop_span()
        logger.debug(f"Ended span {span.name}, duration: {span.duration_ms:.2f}ms")

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[dict] = None,
    ):
        """Context manager for creating spans."""
        span = self.start_span(name, kind, attributes)
        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            self.end_span(span)

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self._traces.get(trace_id)


def trace_agent(tracer: Tracer):
    """Decorator for tracing agent methods."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract agent name from self
            agent_name = args[0].name if args and hasattr(args[0], "name") else func.__name__

            with tracer.span(f"agent.{agent_name}", SpanKind.AGENT) as span:
                span.set_attribute("agent.name", agent_name)
                span.set_attribute("agent.method", func.__name__)

                result = await func(*args, **kwargs)

                # Add result metadata if available
                if hasattr(result, "status"):
                    span.set_attribute("result.status", str(result.status))

                return result

        return wrapper

    return decorator


def trace_tool(tracer: Tracer, tool_name: str):
    """Decorator for tracing tool calls."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.span(f"tool.{tool_name}", SpanKind.TOOL) as span:
                span.set_attribute("tool.name", tool_name)

                result = await func(*args, **kwargs)

                return result

        return wrapper

    return decorator


def trace_llm_call(tracer: Tracer, model: str):
    """Decorator for tracing LLM calls."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with tracer.span(f"llm.{model}", SpanKind.LLM) as span:
                span.set_attribute("llm.model", model)

                start_time = time.time()
                result = await func(*args, **kwargs)

                # Track token usage if available
                if hasattr(result, "usage"):
                    span.set_attribute("llm.input_tokens", result.usage.get("input_tokens", 0))
                    span.set_attribute("llm.output_tokens", result.usage.get("output_tokens", 0))

                span.set_attribute("llm.latency_ms", (time.time() - start_time) * 1000)

                return result

        return wrapper

    return decorator


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


def set_tracer(tracer: Tracer):
    """Set the global tracer instance."""
    global _tracer
    _tracer = tracer
