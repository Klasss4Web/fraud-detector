"""
Shared state models for the fraud detection workflow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AlertSeverity(Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStatus(Enum):
    """Workflow processing status."""

    PENDING = "pending"
    TRIAGING = "triaging"
    GATHERING_CONTEXT = "gathering_context"
    PATTERN_MATCHING = "pattern_matching"
    DECIDING = "deciding"
    EXECUTING_ACTION = "executing_action"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ERROR = "error"


class ActionType(Enum):
    """Types of actions the system can take."""

    APPROVE = "approve"
    BLOCK = "block"
    HOLD = "hold"
    REQUEST_MFA = "request_mfa"
    REQUEST_VERIFICATION = "request_verification"
    FREEZE_ACCOUNT = "freeze_account"
    FLAG_FOR_REVIEW = "flag_for_review"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    NOTIFY_USER = "notify_user"


@dataclass
class ReasoningStep:
    """A single step in the chain of thought reasoning."""

    step_number: int
    hypothesis: str
    evidence: list[str]
    conclusion: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ContextData:
    """Gathered context about the alert."""

    # Identity verification data
    ip_info: Optional[dict[str, Any]] = None
    device_info: Optional[dict[str, Any]] = None
    email_risk: Optional[dict[str, Any]] = None
    phone_risk: Optional[dict[str, Any]] = None

    # Historical data
    user_history: Optional[dict[str, Any]] = None
    transaction_history: Optional[list[dict[str, Any]]] = None
    past_alerts: Optional[list[dict[str, Any]]] = None

    # External checks
    address_verification: Optional[dict[str, Any]] = None
    velocity_check: Optional[dict[str, Any]] = None

    # Computed metrics
    risk_indicators: list[str] = field(default_factory=list)
    anomalies_detected: list[str] = field(default_factory=list)


@dataclass
class PatternMatch:
    """A matched fraud pattern."""

    pattern_id: str
    pattern_name: str
    similarity_score: float
    historical_case_id: Optional[str] = None
    description: str = ""


@dataclass
class Decision:
    """The final decision made by the decider agent."""

    action: ActionType
    confidence: float
    reasoning_chain: list[ReasoningStep]
    risk_score: float
    requires_human_review: bool
    explanation: str
    recommended_followup: list[str] = field(default_factory=list)


@dataclass
class ActionResult:
    """Result of executing an action."""

    action_type: ActionType
    success: bool
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class FraudAlert:
    """Incoming fraud alert to be processed."""

    alert_id: str
    entity_type: str  # transaction, claim, profile, order
    entity_id: str
    entity_data: dict[str, Any]
    initial_risk_score: float
    triggered_rules: list[str]
    timestamp: str
    source: str = "rule_engine"
    priority: int = 0


@dataclass
class WorkflowState:
    """
    Complete state for the fraud detection workflow.
    This is passed between agents in the LangGraph workflow.
    """

    # Input
    alert: FraudAlert

    # Processing state
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_agent: str = ""

    # Triage results
    severity: Optional[AlertSeverity] = None
    requires_immediate_action: bool = False

    # Context gathering results
    context: ContextData = field(default_factory=ContextData)

    # Pattern matching results
    matched_patterns: list[PatternMatch] = field(default_factory=list)

    # Decision
    decision: Optional[Decision] = None

    # Action results
    actions_taken: list[ActionResult] = field(default_factory=list)

    # Human-in-the-loop
    escalated_to_human: bool = False
    human_decision: Optional[dict[str, Any]] = None

    # Audit trail
    processing_log: list[dict[str, Any]] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None

    # Error handling
    errors: list[str] = field(default_factory=list)

    def add_log(self, agent: str, message: str, data: Optional[dict] = None):
        """Add an entry to the processing log."""
        self.processing_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent,
                "message": message,
                "data": data or {},
            }
        )

    def get_explainability_summary(self) -> str:
        """Generate a human-readable explanation of the workflow."""
        lines = [
            f"=== Fraud Alert Analysis: {self.alert.alert_id} ===",
            f"Entity: {self.alert.entity_type} - {self.alert.entity_id}",
            f"Initial Risk Score: {self.alert.initial_risk_score}",
            f"Severity: {self.severity.value if self.severity else 'Not assessed'}",
            "",
        ]

        if self.context.risk_indicators:
            lines.append("Risk Indicators Detected:")
            for indicator in self.context.risk_indicators:
                lines.append(f"  - {indicator}")
            lines.append("")

        if self.matched_patterns:
            lines.append("Matched Fraud Patterns:")
            for pattern in self.matched_patterns:
                lines.append(
                    f"  - {pattern.pattern_name} (similarity: {pattern.similarity_score:.2f})"
                )
            lines.append("")

        if self.decision:
            lines.append("Decision:")
            lines.append(f"  Action: {self.decision.action.value}")
            lines.append(f"  Confidence: {self.decision.confidence:.2%}")
            lines.append(f"  Final Risk Score: {self.decision.risk_score}")
            lines.append("")
            lines.append("Reasoning Chain:")
            for step in self.decision.reasoning_chain:
                lines.append(f"  Step {step.step_number}: {step.hypothesis}")
                lines.append(f"    Evidence: {', '.join(step.evidence)}")
                lines.append(f"    Conclusion: {step.conclusion}")
            lines.append("")
            lines.append(f"Explanation: {self.decision.explanation}")

        if self.escalated_to_human:
            lines.append("\n*** ESCALATED TO HUMAN REVIEW ***")

        return "\n".join(lines)
