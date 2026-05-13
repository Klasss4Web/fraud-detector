"""
Main workflow graph for fraud detection using LangGraph.

This module defines the complete multi-agent workflow that processes
fraud alerts from triage through decision and action execution.
"""

import time
import logging
from typing import Any, Optional, Literal
from datetime import datetime

from workflow.state import (
    WorkflowState,
    WorkflowStatus,
    AlertSeverity,
    FraudAlert,
)
from workflow.triage_agent import TriageAgent
from workflow.context_agent import ContextGathererAgent
from workflow.decider_agent import DeciderAgent
from workflow.action_agent import ActionAgent
from observability import (
    get_tracer,
    get_fraud_metrics,
    get_evaluation_store,
    get_audit_logger,
    SpanKind,
)

logger = logging.getLogger(__name__)


class FraudDetectionWorkflow:
    """
    Orchestrates the multi-agent fraud detection workflow.

    Flow:
    1. Triage Agent - Assesses severity and routes
    2. Context Gatherer Agent - Gathers external context (parallel with Pattern Matcher)
    3. Decider Agent - Makes the final decision with Chain of Thought reasoning
    4. Action Agent - Executes containment/remediation actions
    5. Human Escalation (if needed)
    """

    def __init__(
        self,
        ip_api_key: Optional[str] = None,
        device_api_key: Optional[str] = None,
        email_api_key: Optional[str] = None,
        llm_client: Optional[Any] = None,
    ):
        # Initialize agents
        self.triage_agent = TriageAgent()
        self.context_agent = ContextGathererAgent(
            ip_api_key=ip_api_key,
            device_api_key=device_api_key,
            email_api_key=email_api_key,
        )
        self.decider_agent = DeciderAgent(llm_client=llm_client)
        self.action_agent = ActionAgent()

        # Observability
        self.tracer = get_tracer()
        self.metrics = get_fraud_metrics()
        self.evaluation_store = get_evaluation_store()
        self.audit_logger = get_audit_logger()

    async def process_alert(self, alert: FraudAlert) -> WorkflowState:
        """
        Process a fraud alert through the complete workflow.

        Args:
            alert: The fraud alert to process

        Returns:
            Final workflow state with decision and actions
        """
        start_time = time.time()

        # Start tracing
        trace = self.tracer.start_trace(
            alert_id=alert.alert_id,
            metadata={
                "entity_type": alert.entity_type,
                "entity_id": alert.entity_id,
                "initial_risk_score": alert.initial_risk_score,
            },
        )

        # Record alert received
        self.metrics.record_alert_received(alert.entity_type, alert.source)

        # Initialize workflow state
        state = WorkflowState(alert=alert)

        try:
            # Step 1: Triage
            state = await self._run_triage(state)

            # Step 2: Gather Context
            state = await self._run_context_gathering(state)

            # Step 3: Make Decision
            state = await self._run_decision(state)

            # Step 4: Execute Actions (if not escalated)
            if not state.escalated_to_human:
                state = await self._run_actions(state)

            # Mark completed
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.utcnow().isoformat()

            # Record metrics
            processing_time = time.time() - start_time
            self.metrics.record_alert_processed(
                entity_type=alert.entity_type,
                severity=state.severity.value if state.severity else "unknown",
                decision=state.decision.action.value if state.decision else "none",
                processing_time=processing_time,
            )

            if state.decision:
                self.metrics.record_decision(
                    action=state.decision.action.value,
                    confidence=state.decision.confidence,
                    risk_score=state.decision.risk_score,
                    entity_type=alert.entity_type,
                )

            # Audit log
            if state.decision:
                self.audit_logger.log_decision(
                    alert_id=alert.alert_id,
                    entity_type=alert.entity_type,
                    entity_id=alert.entity_id,
                    decision=state.decision.action.value,
                    risk_score=state.decision.risk_score,
                    confidence=state.decision.confidence,
                    reasoning_summary=state.decision.explanation,
                    actions_taken=[a.action_type.value for a in state.actions_taken],
                    escalated=state.escalated_to_human,
                )

            logger.info(
                f"Workflow completed for {alert.alert_id}: "
                f"decision={state.decision.action.value if state.decision else 'none'}, "
                f"duration={processing_time:.2f}s"
            )

        except Exception as e:
            state.status = WorkflowStatus.ERROR
            state.errors.append(str(e))
            logger.error(f"Workflow error for {alert.alert_id}: {e}")
            raise

        finally:
            self.tracer.end_trace(trace)

        return state

    async def _run_triage(self, state: WorkflowState) -> WorkflowState:
        """Run the triage agent."""
        agent_start = time.time()

        with self.tracer.span("triage", SpanKind.AGENT) as span:
            span.set_attribute("agent.name", "TriageAgent")

            try:
                state = await self.triage_agent.process(state)
                span.set_attribute(
                    "severity", state.severity.value if state.severity else "unknown"
                )
                span.set_attribute("requires_immediate_action", state.requires_immediate_action)

                self.metrics.record_agent_execution(
                    agent_name="TriageAgent",
                    execution_time=time.time() - agent_start,
                )

            except Exception as e:
                self.metrics.record_agent_execution(
                    agent_name="TriageAgent",
                    execution_time=time.time() - agent_start,
                    error=type(e).__name__,
                )
                raise

        return state

    async def _run_context_gathering(self, state: WorkflowState) -> WorkflowState:
        """Run the context gatherer agent."""
        agent_start = time.time()

        with self.tracer.span("context_gathering", SpanKind.AGENT) as span:
            span.set_attribute("agent.name", "ContextGathererAgent")

            try:
                state = await self.context_agent.process(state)
                span.set_attribute("risk_indicators_count", len(state.context.risk_indicators))
                span.set_attribute("anomalies_count", len(state.context.anomalies_detected))

                self.metrics.record_agent_execution(
                    agent_name="ContextGathererAgent",
                    execution_time=time.time() - agent_start,
                )

                # Record tool calls
                if state.context.ip_info:
                    self.metrics.record_tool_call("ip_lookup", True, 0.1)
                if state.context.device_info:
                    self.metrics.record_tool_call("device_lookup", True, 0.1)
                if state.context.email_risk:
                    self.metrics.record_tool_call("email_risk", True, 0.1)

            except Exception as e:
                self.metrics.record_agent_execution(
                    agent_name="ContextGathererAgent",
                    execution_time=time.time() - agent_start,
                    error=type(e).__name__,
                )
                raise

        return state

    async def _run_decision(self, state: WorkflowState) -> WorkflowState:
        """Run the decider agent."""
        agent_start = time.time()

        with self.tracer.span("decision", SpanKind.AGENT) as span:
            span.set_attribute("agent.name", "DeciderAgent")

            try:
                state = await self.decider_agent.process(state)

                if state.decision:
                    span.set_attribute("decision.action", state.decision.action.value)
                    span.set_attribute("decision.confidence", state.decision.confidence)
                    span.set_attribute("decision.risk_score", state.decision.risk_score)
                    span.set_attribute(
                        "decision.requires_human", state.decision.requires_human_review
                    )

                self.metrics.record_agent_execution(
                    agent_name="DeciderAgent",
                    execution_time=time.time() - agent_start,
                )

                # Store for evaluation
                self.evaluation_store.record_agent_execution(
                    agent_name="DeciderAgent",
                    success=True,
                    execution_time=time.time() - agent_start,
                )

            except Exception as e:
                self.metrics.record_agent_execution(
                    agent_name="DeciderAgent",
                    execution_time=time.time() - agent_start,
                    error=type(e).__name__,
                )
                raise

        return state

    async def _run_actions(self, state: WorkflowState) -> WorkflowState:
        """Run the action agent."""
        agent_start = time.time()

        with self.tracer.span("action_execution", SpanKind.AGENT) as span:
            span.set_attribute("agent.name", "ActionAgent")

            try:
                state = await self.action_agent.process(state)

                span.set_attribute("actions_count", len(state.actions_taken))

                # Record each action
                for action in state.actions_taken:
                    self.metrics.record_action(action.action_type.value, action.success)

                    self.audit_logger.log_action_executed(
                        alert_id=state.alert.alert_id,
                        action_type=action.action_type.value,
                        success=action.success,
                        target_entity=state.alert.entity_id,
                        details=action.details,
                    )

                self.metrics.record_agent_execution(
                    agent_name="ActionAgent",
                    execution_time=time.time() - agent_start,
                )

            except Exception as e:
                self.metrics.record_agent_execution(
                    agent_name="ActionAgent",
                    execution_time=time.time() - agent_start,
                    error=type(e).__name__,
                )
                raise

        return state

    def get_workflow_status(self, state: WorkflowState) -> dict[str, Any]:
        """Get a summary of the workflow status."""
        return {
            "alert_id": state.alert.alert_id,
            "status": state.status.value,
            "severity": state.severity.value if state.severity else None,
            "decision": state.decision.action.value if state.decision else None,
            "risk_score": state.decision.risk_score if state.decision else None,
            "confidence": state.decision.confidence if state.decision else None,
            "escalated": state.escalated_to_human,
            "actions_taken": [a.action_type.value for a in state.actions_taken],
            "errors": state.errors,
            "duration_ms": (
                (
                    datetime.fromisoformat(state.completed_at)
                    - datetime.fromisoformat(state.started_at)
                ).total_seconds()
                * 1000
                if state.completed_at
                else None
            ),
        }


def create_workflow(
    ip_api_key: Optional[str] = None,
    device_api_key: Optional[str] = None,
    email_api_key: Optional[str] = None,
    llm_client: Optional[Any] = None,
) -> FraudDetectionWorkflow:
    """Create a new fraud detection workflow instance."""
    return FraudDetectionWorkflow(
        ip_api_key=ip_api_key,
        device_api_key=device_api_key,
        email_api_key=email_api_key,
        llm_client=llm_client,
    )
