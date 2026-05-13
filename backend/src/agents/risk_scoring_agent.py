"""
Risk Scoring Agent with ML Integration
=======================================

Aggregates signals from all specialized agents and uses
machine learning to calculate unified risk scores.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from dataclasses import dataclass
from .base_agent import BaseAgent, AgentResult, FraudSignal, RiskLevel


@dataclass
class AggregatedRisk:
    """Aggregated risk assessment from multiple agents"""

    entity_id: str
    entity_type: str  # transaction, claim, profile, order
    final_risk_score: float
    risk_level: RiskLevel
    agent_scores: Dict[str, float]
    top_signals: List[FraudSignal]
    recommendation: str
    confidence: float
    requires_investigation: bool


class RiskScoringAgent(BaseAgent):
    """
    Agent that aggregates results from specialized agents
    and applies ML-based scoring adjustments.
    """

    # Weight factors for different agent types
    AGENT_WEIGHTS = {
        "TransactionFraudAgent": 0.30,
        "InsuranceFraudAgent": 0.30,
        "IdentityFraudAgent": 0.25,
        "EcommerceFraudAgent": 0.30,
    }

    # Signal category weights for ML-like scoring
    CATEGORY_WEIGHTS = {
        "velocity": 1.2,
        "amount": 1.0,
        "location": 1.1,
        "device": 0.9,
        "time": 0.7,
        "security": 1.3,
        "history": 1.2,
        "verification": 1.0,
        "synthetic": 1.4,
        "chargeback": 1.5,
        "behavior": 1.1,
    }

    def __init__(self):
        super().__init__("RiskScoringAgent")
        self._feature_importance = None

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """Not used directly - use aggregate() instead"""
        raise NotImplementedError("Use aggregate() method instead")

    def aggregate(
        self, results: List[AgentResult], entity_id: str, entity_type: str
    ) -> AggregatedRisk:
        """
        Aggregate results from multiple specialized agents.

        Args:
            results: List of AgentResult from specialized agents
            entity_id: Identifier of the entity being analyzed
            entity_type: Type of entity (transaction, claim, profile, order)

        Returns:
            AggregatedRisk with final assessment
        """
        self.log(
            f"Aggregating {len(results)} agent results for {entity_type} {entity_id}"
        )

        if not results:
            return self._create_low_risk_result(entity_id, entity_type)

        # Collect all scores and signals
        agent_scores = {}
        all_signals = []

        for result in results:
            agent_scores[result.agent_name] = result.risk_score
            all_signals.extend(result.signals)

        # Calculate weighted base score
        weighted_score = self._calculate_weighted_score(agent_scores)

        # Apply ML-like adjustments based on signal patterns
        adjusted_score = self._apply_signal_adjustments(weighted_score, all_signals)

        # Apply cross-signal correlation boost
        correlation_boost = self._calculate_correlation_boost(all_signals)
        final_score = min(100, adjusted_score + correlation_boost)

        # Calculate confidence based on signal agreement
        confidence = self._calculate_confidence(results, all_signals)

        # Get top signals
        top_signals = self._get_top_signals(all_signals, limit=5)

        # Determine risk level
        risk_level = self._calculate_risk_level(final_score)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            final_score, risk_level, entity_type, top_signals
        )

        # Determine if investigation is needed
        requires_investigation = (
            final_score >= 60
            or any(s.weight >= 0.8 for s in top_signals)
            or len([s for s in all_signals if s.category == "security"]) > 0
        )

        self.log(f"Final risk score: {final_score:.1f} ({risk_level.value})")

        return AggregatedRisk(
            entity_id=entity_id,
            entity_type=entity_type,
            final_risk_score=round(final_score, 2),
            risk_level=risk_level,
            agent_scores=agent_scores,
            top_signals=top_signals,
            recommendation=recommendation,
            confidence=round(confidence, 2),
            requires_investigation=requires_investigation,
        )

    def _calculate_weighted_score(self, agent_scores: Dict[str, float]) -> float:
        """Calculate weighted average of agent scores"""
        if not agent_scores:
            return 0.0

        total_weight = 0
        weighted_sum = 0

        for agent_name, score in agent_scores.items():
            weight = self.AGENT_WEIGHTS.get(agent_name, 0.25)
            weighted_sum += score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _apply_signal_adjustments(
        self, base_score: float, signals: List[FraudSignal]
    ) -> float:
        """Apply ML-like adjustments based on signal categories"""
        if not signals:
            return base_score

        # Calculate category-weighted signal contribution
        category_scores = {}
        for signal in signals:
            category = signal.category
            weight = self.CATEGORY_WEIGHTS.get(category, 1.0)

            if category not in category_scores:
                category_scores[category] = 0
            category_scores[category] += signal.weight * weight * 10

        # Apply adjustment (capped)
        adjustment = sum(category_scores.values()) / max(len(category_scores), 1)
        adjusted = base_score + adjustment * 0.5

        return min(100, adjusted)

    def _calculate_correlation_boost(self, signals: List[FraudSignal]) -> float:
        """
        Calculate boost for correlated signals across categories.
        Multiple signals in different categories indicate higher risk.
        """
        unique_categories = set(s.category for s in signals)
        high_weight_signals = [s for s in signals if s.weight >= 0.6]

        # Boost for signals in multiple categories
        category_boost = len(unique_categories) * 2

        # Boost for multiple high-weight signals
        high_weight_boost = len(high_weight_signals) * 3

        return min(15, category_boost + high_weight_boost)

    def _calculate_confidence(
        self, results: List[AgentResult], signals: List[FraudSignal]
    ) -> float:
        """Calculate confidence score based on agent agreement and signal strength"""
        if not results:
            return 0.5

        # Base confidence from agent confidence scores
        base_confidence = np.mean([r.confidence for r in results])

        # Adjust based on score agreement
        scores = [r.risk_score for r in results]
        if len(scores) > 1:
            score_std = np.std(scores)
            agreement_factor = 1 - min(1, score_std / 50)
        else:
            agreement_factor = 0.8

        # Adjust based on signal strength
        if signals:
            avg_weight = np.mean([s.weight for s in signals])
            signal_factor = avg_weight
        else:
            signal_factor = 0.5

        confidence = (
            base_confidence * 0.4 + agreement_factor * 0.3 + signal_factor * 0.3
        )
        return min(1.0, max(0.0, confidence))

    def _get_top_signals(
        self, signals: List[FraudSignal], limit: int = 5
    ) -> List[FraudSignal]:
        """Get top signals by weight"""
        sorted_signals = sorted(signals, key=lambda s: s.weight, reverse=True)

        # Deduplicate by name
        seen = set()
        unique_signals = []
        for signal in sorted_signals:
            if signal.name not in seen:
                seen.add(signal.name)
                unique_signals.append(signal)

        return unique_signals[:limit]

    def _calculate_risk_level(self, score: float) -> RiskLevel:
        """Convert score to risk level"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _generate_recommendation(
        self,
        score: float,
        risk_level: RiskLevel,
        entity_type: str,
        top_signals: List[FraudSignal],
    ) -> str:
        """Generate comprehensive recommendation"""

        entity_actions = {
            "transaction": {
                RiskLevel.CRITICAL: "BLOCK immediately. Alert fraud team.",
                RiskLevel.HIGH: "HOLD for verification. Request additional authentication.",
                RiskLevel.MEDIUM: "ALLOW with enhanced monitoring.",
                RiskLevel.LOW: "APPROVE. Standard monitoring.",
            },
            "claim": {
                RiskLevel.CRITICAL: "DENY and refer to SIU for investigation.",
                RiskLevel.HIGH: "SUSPEND processing. Conduct field investigation.",
                RiskLevel.MEDIUM: "REQUEST additional documentation.",
                RiskLevel.LOW: "PROCESS normally with standard verification.",
            },
            "profile": {
                RiskLevel.CRITICAL: "SUSPEND account. Require identity verification.",
                RiskLevel.HIGH: "RESTRICT account. Enhanced KYC required.",
                RiskLevel.MEDIUM: "MONITOR closely. Step-up authentication.",
                RiskLevel.LOW: "NO ACTION required.",
            },
            "order": {
                RiskLevel.CRITICAL: "CANCEL order. Potential fraud.",
                RiskLevel.HIGH: "HOLD shipment. Manual review required.",
                RiskLevel.MEDIUM: "VERIFY before shipping.",
                RiskLevel.LOW: "SHIP normally.",
            },
        }

        action = entity_actions.get(entity_type, {}).get(
            risk_level, "Review according to standard procedures."
        )

        # Add signal-specific guidance
        if top_signals:
            top_signal = top_signals[0]
            action += f" Primary concern: {top_signal.description}"

        return action

    def _create_low_risk_result(
        self, entity_id: str, entity_type: str
    ) -> AggregatedRisk:
        """Create a low-risk result when no agents provided input"""
        return AggregatedRisk(
            entity_id=entity_id,
            entity_type=entity_type,
            final_risk_score=0.0,
            risk_level=RiskLevel.LOW,
            agent_scores={},
            top_signals=[],
            recommendation="No risk signals detected. Process normally.",
            confidence=0.5,
            requires_investigation=False,
        )

    def batch_aggregate(
        self, batch_results: List[Dict[str, Any]]
    ) -> List[AggregatedRisk]:
        """
        Process multiple entities in batch.

        Args:
            batch_results: List of dicts with keys:
                - entity_id: str
                - entity_type: str
                - agent_results: List[AgentResult]

        Returns:
            List of AggregatedRisk
        """
        self.log(f"Processing batch of {len(batch_results)} entities")

        aggregated = []
        for item in batch_results:
            result = self.aggregate(
                results=item["agent_results"],
                entity_id=item["entity_id"],
                entity_type=item["entity_type"],
            )
            aggregated.append(result)

        # Sort by risk score descending
        aggregated.sort(key=lambda x: x.final_risk_score, reverse=True)

        return aggregated
