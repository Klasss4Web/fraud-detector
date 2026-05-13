"""
Logging configuration for fraud detection system.

Provides structured logging with contextual information
for debugging and auditing.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class StructuredLogRecord:
    """A structured log record."""

    timestamp: str
    level: str
    logger: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    alert_id: Optional[str] = None
    agent_name: Optional[str] = None
    extra: dict[str, Any] = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
        }
        if self.trace_id:
            result["trace_id"] = self.trace_id
        if self.span_id:
            result["span_id"] = self.span_id
        if self.alert_id:
            result["alert_id"] = self.alert_id
        if self.agent_name:
            result["agent_name"] = self.agent_name
        if self.extra:
            result["extra"] = self.extra
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs structured JSON logs.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Extract extra fields
        extra = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "trace_id",
                "span_id",
                "alert_id",
                "agent_name",
            }:
                extra[key] = value

        log_record = StructuredLogRecord(
            timestamp=datetime.utcnow().isoformat(),
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            trace_id=getattr(record, "trace_id", None),
            span_id=getattr(record, "span_id", None),
            alert_id=getattr(record, "alert_id", None),
            agent_name=getattr(record, "agent_name", None),
            extra=extra if extra else None,
        )

        return log_record.to_json()


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable formatter for console output.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)

        # Build context string
        context_parts = []
        if hasattr(record, "trace_id") and record.trace_id:
            context_parts.append(f"trace={record.trace_id[:8]}")
        if hasattr(record, "alert_id") and record.alert_id:
            context_parts.append(f"alert={record.alert_id}")
        if hasattr(record, "agent_name") and record.agent_name:
            context_parts.append(f"agent={record.agent_name}")

        context = f" [{', '.join(context_parts)}]" if context_parts else ""

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        return (
            f"{color}[{timestamp}] [{record.levelname}]{self.RESET} "
            f"[{record.name}]{context} {record.getMessage()}"
        )


class ContextLogger:
    """
    Logger wrapper that automatically includes context.
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context: dict[str, Any] = {}

    def set_context(self, **kwargs):
        """Set context values that will be included in all logs."""
        self._context.update(kwargs)

    def clear_context(self):
        """Clear all context values."""
        self._context.clear()

    def _log(self, level: int, msg: str, *args, **kwargs):
        """Internal logging method that adds context."""
        extra = kwargs.pop("extra", {})
        extra.update(self._context)
        kwargs["extra"] = extra
        self._logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Whether to output structured JSON logs
        log_file: Optional file path for log output
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(console_handler)

    # File handler (always JSON)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Set levels for third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger."""
    return ContextLogger(logging.getLogger(name))


class AuditLogger:
    """
    Special logger for audit trail of fraud decisions.

    This creates an immutable log of all decisions for compliance.
    """

    def __init__(self, log_file: str = "audit.log"):
        self._logger = logging.getLogger("fraud_detection.audit")
        self._logger.setLevel(logging.INFO)

        # Audit logs always go to file in JSON format
        handler = logging.FileHandler(log_file)
        handler.setFormatter(StructuredFormatter())
        self._logger.addHandler(handler)

        # Prevent propagation to root logger
        self._logger.propagate = False

    def log_decision(
        self,
        alert_id: str,
        entity_type: str,
        entity_id: str,
        decision: str,
        risk_score: float,
        confidence: float,
        reasoning_summary: str,
        actions_taken: list[str],
        escalated: bool,
    ):
        """Log a fraud decision for audit purposes."""
        self._logger.info(
            "FRAUD_DECISION",
            extra={
                "event_type": "fraud_decision",
                "alert_id": alert_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "decision": decision,
                "risk_score": risk_score,
                "confidence": confidence,
                "reasoning_summary": reasoning_summary,
                "actions_taken": actions_taken,
                "escalated": escalated,
            },
        )

    def log_human_override(
        self,
        alert_id: str,
        original_decision: str,
        human_decision: str,
        analyst_id: str,
        reason: str,
    ):
        """Log when a human overrides an agent decision."""
        self._logger.info(
            "HUMAN_OVERRIDE",
            extra={
                "event_type": "human_override",
                "alert_id": alert_id,
                "original_decision": original_decision,
                "human_decision": human_decision,
                "analyst_id": analyst_id,
                "reason": reason,
            },
        )

    def log_action_executed(
        self,
        alert_id: str,
        action_type: str,
        success: bool,
        target_entity: str,
        details: dict[str, Any],
    ):
        """Log when an action is executed."""
        self._logger.info(
            "ACTION_EXECUTED",
            extra={
                "event_type": "action_executed",
                "alert_id": alert_id,
                "action_type": action_type,
                "success": success,
                "target_entity": target_entity,
                "details": details,
            },
        )


# Global audit logger
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
