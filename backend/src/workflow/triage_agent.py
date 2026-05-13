"""
Triage Agent - Assesses severity and routes alerts.

The Triage Agent is the first line of defense. It quickly assesses
incoming alerts and determines:
1. Alert severity (low, medium, high, critical)
2. Whether immediate action is required
3. Which downstream agents should be involved
"""

import logging
from typing import Any
from datetime import datetime

from workflow.state import (
    WorkflowState,
    WorkflowStatus,
    AlertSeverity,
    FraudAlert,
)

logger = logging.getLogger(__name__)


class TriageAgent:
    """
    Assesses incoming fraud alerts and routes them appropriately.
    """

    # Thresholds for severity classification
    CRITICAL_THRESHOLD = 80.0
    HIGH_THRESHOLD = 60.0
    MEDIUM_THRESHOLD = 40.0

    # High-value transaction thresholds
    HIGH_VALUE_THRESHOLDS = {
        "transaction": 5000.0,
        "claim": 25000.0,
        "order": 2000.0,
    }

    # Rules that indicate critical fraud patterns
    CRITICAL_RULES = {
        "impossible_travel",
        "known_fraud_device",
        "synthetic_identity",
        "account_takeover",
        "velocity_attack",
        "card_testing",
    }

    def __init__(self):
        self.name = "TriageAgent"

    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Process an alert and determine severity/routing.

        Args:
            state: Current workflow state with the alert

        Returns:
            Updated workflow state with triage results
        """
        state.status = WorkflowStatus.TRIAGING
        state.current_agent = self.name
        state.add_log(self.name, "Starting triage assessment")

        alert = state.alert

        # Assess severity
        severity = self._assess_severity(alert)
        state.severity = severity

        # Check if immediate action is required
        state.requires_immediate_action = self._requires_immediate_action(alert, severity)

        # Log the triage decision
        state.add_log(
            self.name,
            f"Triage complete: severity={severity.value}, immediate_action={state.requires_immediate_action}",
            {
                "severity": severity.value,
                "risk_score": alert.initial_risk_score,
                "triggered_rules": alert.triggered_rules,
                "requires_immediate_action": state.requires_immediate_action,
            },
        )

        logger.info(
            f"Alert {alert.alert_id} triaged: severity={severity.value}, "
            f"immediate_action={state.requires_immediate_action}"
        )

        return state

    def _assess_severity(self, alert: FraudAlert) -> AlertSeverity:
        """Determine alert severity based on risk score and rules."""

        # Check for critical rules first
        if any(rule in self.CRITICAL_RULES for rule in alert.triggered_rules):
            return AlertSeverity.CRITICAL

        # Check high-value transactions
        entity_value = self._get_entity_value(alert)
        threshold = self.HIGH_VALUE_THRESHOLDS.get(alert.entity_type, 5000.0)

        if entity_value and entity_value > threshold * 2:
            # Very high value - bump severity
            if alert.initial_risk_score >= self.MEDIUM_THRESHOLD:
                return AlertSeverity.CRITICAL

        # Classify based on risk score
        if alert.initial_risk_score >= self.CRITICAL_THRESHOLD:
            return AlertSeverity.CRITICAL
        elif alert.initial_risk_score >= self.HIGH_THRESHOLD:
            return AlertSeverity.HIGH
        elif alert.initial_risk_score >= self.MEDIUM_THRESHOLD:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    def _get_entity_value(self, alert: FraudAlert) -> float | None:
        """Extract monetary value from the alert entity."""
        data = alert.entity_data

        # Look for common value fields
        value_fields = ["amount", "claim_amount", "order_total", "total_amount", "value"]

        for field in value_fields:
            if field in data:
                try:
                    return float(data[field])
                except (ValueError, TypeError):
                    continue

        return None

    def _requires_immediate_action(self, alert: FraudAlert, severity: AlertSeverity) -> bool:
        """Determine if the alert requires immediate automated action."""

        # Critical alerts always require immediate action
        if severity == AlertSeverity.CRITICAL:
            return True

        # High severity with certain rule triggers
        high_priority_rules = {
            "velocity_attack",
            "card_testing",
            "account_takeover",
            "known_fraud_ip",
        }

        if severity == AlertSeverity.HIGH:
            if any(rule in high_priority_rules for rule in alert.triggered_rules):
                return True

        return False

    def get_recommended_agents(self, state: WorkflowState) -> list[str]:
        """
        Determine which downstream agents should process this alert.

        Returns:
            List of agent names that should process this alert
        """
        agents = ["ContextGathererAgent", "PatternMatcherAgent"]

        # Always include the decider
        agents.append("DeciderAgent")

        # For critical/high, include action agent
        if state.severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH):
            agents.append("ActionAgent")

        # For medium with ambiguous scores, might need human
        if state.severity == AlertSeverity.MEDIUM:
            agents.append("HumanEscalationAgent")

        return agents
