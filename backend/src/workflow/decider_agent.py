"""
Decider Agent - Makes the final fraud decision with Chain of Thought reasoning.

This is the "brain" of the system. It weighs all evidence, performs
structured reasoning, and makes the final determination with full explainability.
"""

import logging
from typing import Any, Optional
from datetime import datetime

from workflow.state import (
    WorkflowState,
    WorkflowStatus,
    AlertSeverity,
    ActionType,
    Decision,
    ReasoningStep,
)

logger = logging.getLogger(__name__)


class DeciderAgent:
    """
    Makes final fraud decisions using Chain of Thought reasoning.
    """

    # Confidence thresholds for human escalation
    ESCALATION_CONFIDENCE_LOW = 0.40
    ESCALATION_CONFIDENCE_HIGH = 0.70

    # Value thresholds for mandatory human review
    MANDATORY_REVIEW_THRESHOLDS = {
        "transaction": 10000.0,
        "claim": 50000.0,
        "order": 5000.0,
    }

    def __init__(self, llm_client: Optional[Any] = None):
        self.name = "DeciderAgent"
        self.llm_client = llm_client  # Optional LLM for enhanced reasoning

    async def process(self, state: WorkflowState) -> WorkflowState:
        """
        Make the final fraud decision.

        Args:
            state: Current workflow state with all gathered context

        Returns:
            Updated state with decision
        """
        state.status = WorkflowStatus.DECIDING
        state.current_agent = self.name
        state.add_log(self.name, "Starting decision process")

        # Perform Chain of Thought reasoning
        reasoning_chain = await self._perform_reasoning(state)

        # Calculate final risk score
        final_risk_score = self._calculate_final_risk(state, reasoning_chain)

        # Determine action
        action, confidence = self._determine_action(state, final_risk_score, reasoning_chain)

        # Check if human review is required
        requires_human = self._requires_human_review(state, confidence, final_risk_score)

        # Generate explanation
        explanation = self._generate_explanation(state, reasoning_chain, action)

        # Build decision
        decision = Decision(
            action=action,
            confidence=confidence,
            reasoning_chain=reasoning_chain,
            risk_score=final_risk_score,
            requires_human_review=requires_human,
            explanation=explanation,
            recommended_followup=self._get_recommended_followup(action, state),
        )

        state.decision = decision

        state.add_log(
            self.name,
            f"Decision made: {action.value} (confidence: {confidence:.2%})",
            {
                "action": action.value,
                "confidence": confidence,
                "risk_score": final_risk_score,
                "requires_human": requires_human,
            },
        )

        logger.info(
            f"Decision for {state.alert.alert_id}: {action.value} "
            f"(confidence: {confidence:.2%}, risk: {final_risk_score:.1f})"
        )

        return state

    async def _perform_reasoning(self, state: WorkflowState) -> list[ReasoningStep]:
        """
        Perform structured Chain of Thought reasoning.

        This creates an auditable trail of how the decision was made.
        """
        steps = []
        step_num = 1

        # Step 1: Assess initial alert signals
        initial_hypothesis = f"Alert triggered with {len(state.alert.triggered_rules)} rule(s)"
        initial_evidence = state.alert.triggered_rules.copy()
        initial_conclusion = self._assess_initial_signals(state)

        steps.append(
            ReasoningStep(
                step_number=step_num,
                hypothesis=initial_hypothesis,
                evidence=initial_evidence,
                conclusion=initial_conclusion,
                confidence=0.6 if state.alert.initial_risk_score > 50 else 0.4,
            )
        )
        step_num += 1

        # Step 2: Analyze gathered context
        context = state.context
        context_evidence = []

        if context.ip_info:
            ip_risk = context.ip_info.get("risk_score", 0)
            if ip_risk > 50:
                context_evidence.append(f"High-risk IP (score: {ip_risk})")
            if context.ip_info.get("is_vpn"):
                context_evidence.append("VPN/Proxy detected")

        if context.device_info:
            if context.device_info.get("is_emulator"):
                context_evidence.append("Emulator detected")
            if context.device_info.get("associated_users", 1) > 3:
                context_evidence.append("Device shared by multiple users")

        if context.email_risk:
            if context.email_risk.get("is_disposable"):
                context_evidence.append("Disposable email")
            if context.email_risk.get("domain_age_days", 365) < 30:
                context_evidence.append("Very new email domain")

        if context.velocity_check:
            if "HIGH_VELOCITY" in context.velocity_check.get("flags", []):
                context_evidence.append("High transaction velocity")

        context_conclusion = self._assess_context(context_evidence)

        steps.append(
            ReasoningStep(
                step_number=step_num,
                hypothesis="Analyzing external context and risk indicators",
                evidence=context_evidence or ["No significant context indicators found"],
                conclusion=context_conclusion,
                confidence=0.7 if len(context_evidence) > 2 else 0.5,
            )
        )
        step_num += 1

        # Step 3: Analyze anomalies
        anomalies = context.anomalies_detected
        if anomalies:
            anomaly_conclusion = self._assess_anomalies(anomalies)
            steps.append(
                ReasoningStep(
                    step_number=step_num,
                    hypothesis="Evaluating detected anomalies",
                    evidence=anomalies,
                    conclusion=anomaly_conclusion,
                    confidence=0.8 if len(anomalies) > 1 else 0.6,
                )
            )
            step_num += 1

        # Step 4: Pattern matching results
        if state.matched_patterns:
            pattern_evidence = [
                f"{p.pattern_name} (similarity: {p.similarity_score:.2f})"
                for p in state.matched_patterns
            ]
            steps.append(
                ReasoningStep(
                    step_number=step_num,
                    hypothesis="Comparing against known fraud patterns",
                    evidence=pattern_evidence,
                    conclusion="Matches found with historical fraud patterns",
                    confidence=max(p.similarity_score for p in state.matched_patterns),
                )
            )
            step_num += 1

        # Step 5: Final synthesis
        all_evidence = []
        for step in steps:
            all_evidence.extend(step.evidence)

        final_conclusion = self._synthesize_conclusion(steps)
        avg_confidence = sum(s.confidence for s in steps) / len(steps) if steps else 0.5

        steps.append(
            ReasoningStep(
                step_number=step_num,
                hypothesis="Synthesizing all evidence for final determination",
                evidence=[f"Based on {len(all_evidence)} total evidence points"],
                conclusion=final_conclusion,
                confidence=avg_confidence,
            )
        )

        return steps

    def _assess_initial_signals(self, state: WorkflowState) -> str:
        """Assess the initial alert signals."""
        score = state.alert.initial_risk_score
        rules = state.alert.triggered_rules

        if score >= 80:
            return "Initial signals indicate CRITICAL risk level"
        elif score >= 60:
            return "Initial signals indicate HIGH risk level"
        elif score >= 40:
            return f"Moderate risk indicated by {len(rules)} triggered rules"
        else:
            return "Low initial risk, proceeding with detailed analysis"

    def _assess_context(self, evidence: list[str]) -> str:
        """Assess gathered context evidence."""
        if len(evidence) >= 4:
            return "Multiple high-risk indicators present - strong fraud signals"
        elif len(evidence) >= 2:
            return "Several risk indicators warrant careful review"
        elif len(evidence) == 1:
            return "Single risk indicator noted, may be benign"
        else:
            return "No significant risk indicators from context analysis"

    def _assess_anomalies(self, anomalies: list[str]) -> str:
        """Assess detected anomalies."""
        critical_anomalies = {"IMPOSSIBLE_TRAVEL", "EMULATOR_DETECTED", "SYNTHETIC_IDENTITY"}

        if any(a in critical_anomalies for a in anomalies):
            return "Critical anomaly detected - high likelihood of fraud"
        elif len(anomalies) >= 2:
            return "Multiple anomalies suggest coordinated fraud attempt"
        else:
            return "Anomaly noted but may have legitimate explanation"

    def _synthesize_conclusion(self, steps: list[ReasoningStep]) -> str:
        """Synthesize all reasoning steps into final conclusion."""
        high_confidence_conclusions = [s for s in steps if s.confidence >= 0.7]

        if len(high_confidence_conclusions) >= 2:
            return "Strong evidence supports fraud determination"
        elif len(high_confidence_conclusions) == 1:
            return "Moderate evidence of fraud - additional verification recommended"
        else:
            return "Insufficient evidence for definitive fraud determination"

    def _calculate_final_risk(self, state: WorkflowState, reasoning: list[ReasoningStep]) -> float:
        """Calculate the final risk score incorporating all evidence."""
        base_score = state.alert.initial_risk_score

        # Adjust based on context
        context = state.context
        adjustments = 0.0

        if context.ip_info:
            ip_risk = context.ip_info.get("risk_score", 0)
            adjustments += (ip_risk - 50) * 0.1  # Scale IP risk contribution

        if context.device_info:
            device_risk = context.device_info.get("risk_score", 0)
            adjustments += (device_risk - 50) * 0.1

        if context.email_risk:
            email_risk = context.email_risk.get("risk_score", 0)
            adjustments += (email_risk - 50) * 0.1

        # Boost for anomalies
        anomaly_count = len(context.anomalies_detected)
        adjustments += anomaly_count * 5

        # Pattern match boost
        if state.matched_patterns:
            max_similarity = max(p.similarity_score for p in state.matched_patterns)
            adjustments += max_similarity * 15

        final_score = base_score + adjustments
        return max(0, min(100, final_score))

    def _determine_action(
        self, state: WorkflowState, risk_score: float, reasoning: list[ReasoningStep]
    ) -> tuple[ActionType, float]:
        """Determine the appropriate action based on risk assessment."""

        # Get average confidence from reasoning
        avg_confidence = sum(s.confidence for s in reasoning) / len(reasoning) if reasoning else 0.5

        # Decision matrix
        if risk_score >= 85:
            return ActionType.BLOCK, min(0.95, avg_confidence + 0.1)
        elif risk_score >= 70:
            if state.severity == AlertSeverity.CRITICAL:
                return ActionType.FREEZE_ACCOUNT, avg_confidence
            return ActionType.BLOCK, avg_confidence
        elif risk_score >= 55:
            return ActionType.REQUEST_MFA, avg_confidence
        elif risk_score >= 40:
            return ActionType.FLAG_FOR_REVIEW, max(0.4, avg_confidence - 0.1)
        else:
            return ActionType.APPROVE, avg_confidence

    def _requires_human_review(
        self, state: WorkflowState, confidence: float, risk_score: float
    ) -> bool:
        """Determine if human review is required."""

        # Ambiguous confidence requires human
        if self.ESCALATION_CONFIDENCE_LOW <= confidence <= self.ESCALATION_CONFIDENCE_HIGH:
            return True

        # High value transactions require human
        entity_value = self._get_entity_value(state.alert.entity_data)
        threshold = self.MANDATORY_REVIEW_THRESHOLDS.get(state.alert.entity_type, 10000.0)

        if entity_value and entity_value > threshold:
            return True

        # Medium risk with conflicting signals
        if 40 <= risk_score <= 65 and len(state.context.anomalies_detected) > 0:
            return True

        return False

    def _get_entity_value(self, data: dict) -> float | None:
        """Extract monetary value from entity data."""
        for field in ["amount", "claim_amount", "order_total", "total_amount"]:
            if field in data:
                try:
                    return float(data[field])
                except (ValueError, TypeError):
                    continue
        return None

    def _generate_explanation(
        self, state: WorkflowState, reasoning: list[ReasoningStep], action: ActionType
    ) -> str:
        """Generate human-readable explanation of the decision."""

        # Collect key evidence
        key_points = []

        for step in reasoning:
            if step.confidence >= 0.6:
                key_points.append(step.conclusion)

        # Build explanation
        explanation_parts = [
            f"Decision: {action.value.upper()}",
            "",
            "Key findings:",
        ]

        for point in key_points[:5]:  # Limit to top 5
            explanation_parts.append(f"  - {point}")

        if state.context.risk_indicators:
            explanation_parts.append("")
            explanation_parts.append("Risk indicators:")
            for indicator in state.context.risk_indicators[:3]:
                explanation_parts.append(f"  - {indicator}")

        return "\n".join(explanation_parts)

    def _get_recommended_followup(self, action: ActionType, state: WorkflowState) -> list[str]:
        """Get recommended follow-up actions."""
        followups = []

        if action in (ActionType.BLOCK, ActionType.FREEZE_ACCOUNT):
            followups.append("Notify user of security concern")
            followups.append("Review related accounts for similar patterns")

        if action == ActionType.REQUEST_MFA:
            followups.append("Monitor for MFA completion within 15 minutes")
            followups.append("Block if MFA not completed")

        if action == ActionType.FLAG_FOR_REVIEW:
            followups.append("Manual analyst review within 24 hours")
            followups.append("Gather additional user history if needed")

        return followups
