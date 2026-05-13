"""
Insurance Fraud Detection Agent
================================

Specialized agent for detecting insurance claims fraud:
- Staged incidents
- Exaggerated claims
- Serial claimants
- Policy timing patterns
- Suspicious claim patterns
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult, FraudSignal


class InsuranceFraudAgent(BaseAgent):
    """Agent specialized in detecting insurance claims fraud"""

    # Thresholds
    HIGH_CLAIM_THRESHOLD = 25000
    VERY_HIGH_CLAIM_THRESHOLD = 75000
    SERIAL_CLAIMANT_THRESHOLD = 3
    NEW_POLICY_DAYS = 90
    QUICK_CLAIM_DAYS = 3

    SUSPICIOUS_DESCRIPTIONS = [
        "stolen",
        "break-in",
        "burglary",
        "theft",
        "total loss",
        "severe",
        "extensive damage",
    ]

    def __init__(self):
        super().__init__("InsuranceFraudAgent")

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """Analyze an insurance claim for fraud signals"""
        self.log(f"Analyzing claim {data.get('claim_id', 'unknown')}")

        signals = []
        risk_score = 0

        # 1. Claim Amount Analysis
        amount_score, amount_signals = self._analyze_amount(data)
        risk_score += amount_score
        signals.extend(amount_signals)

        # 2. Timing Analysis
        timing_score, timing_signals = self._analyze_timing(data)
        risk_score += timing_score
        signals.extend(timing_signals)

        # 3. Claimant History
        history_score, history_signals = self._analyze_history(data)
        risk_score += history_score
        signals.extend(history_signals)

        # 4. Witness Analysis
        witness_score, witness_signals = self._analyze_witnesses(data)
        risk_score += witness_score
        signals.extend(witness_signals)

        # 5. Description Analysis
        desc_score, desc_signals = self._analyze_description(data)
        risk_score += desc_score
        signals.extend(desc_signals)

        # Generate recommendation
        recommendation = self._generate_recommendation(risk_score, signals, data)

        return self._create_result(
            entity_id=data.get("claim_id", "unknown"),
            risk_score=risk_score,
            signals=signals,
            recommendation=recommendation,
            details={
                "claim_amount": data.get("claim_amount"),
                "claim_type": data.get("claim_type"),
                "policy_age_days": data.get("policy_age_days"),
                "previous_claims": data.get("previous_claims_count"),
            },
        )

    def _analyze_amount(self, data: Dict[str, Any]) -> tuple:
        """Analyze claim amount for suspicious patterns"""
        signals = []
        score = 0

        amount = data.get("claim_amount", 0)

        if amount > self.VERY_HIGH_CLAIM_THRESHOLD:
            score += 25
            signals.append(
                FraudSignal(
                    name="very_high_claim",
                    description=f"Very high claim amount: ${amount:,.2f}",
                    weight=0.85,
                    category="amount",
                )
            )
        elif amount > self.HIGH_CLAIM_THRESHOLD:
            score += 15
            signals.append(
                FraudSignal(
                    name="high_claim",
                    description=f"High claim amount: ${amount:,.2f}",
                    weight=0.6,
                    category="amount",
                )
            )

        # Round number suspicion (common in fraudulent claims)
        if amount > 1000 and amount == int(amount) and amount % 1000 == 0:
            score += 5
            signals.append(
                FraudSignal(
                    name="round_amount",
                    description="Suspiciously round claim amount",
                    weight=0.3,
                    category="amount",
                )
            )

        return score, signals

    def _analyze_timing(self, data: Dict[str, Any]) -> tuple:
        """Analyze policy and claim timing patterns"""
        signals = []
        score = 0

        policy_age = data.get("policy_age_days", 365)
        time_to_claim = data.get("time_to_claim_days", 7)

        # New policy with claim
        if policy_age < self.NEW_POLICY_DAYS:
            score += 20
            signals.append(
                FraudSignal(
                    name="new_policy_claim",
                    description=f"Claim on new policy ({policy_age} days old)",
                    weight=0.7,
                    category="timing",
                )
            )

        # Very quick claim after incident
        if time_to_claim <= self.QUICK_CLAIM_DAYS:
            score += 15
            signals.append(
                FraudSignal(
                    name="quick_claim",
                    description=f"Claim filed very quickly ({time_to_claim} days after incident)",
                    weight=0.6,
                    category="timing",
                )
            )

        # Very delayed claim (potential for fabrication)
        if time_to_claim > 30:
            score += 10
            signals.append(
                FraudSignal(
                    name="delayed_claim",
                    description=f"Significantly delayed claim ({time_to_claim} days)",
                    weight=0.4,
                    category="timing",
                )
            )

        return score, signals

    def _analyze_history(self, data: Dict[str, Any]) -> tuple:
        """Analyze claimant's claims history"""
        signals = []
        score = 0

        previous_claims = data.get("previous_claims_count", 0)

        if previous_claims >= self.SERIAL_CLAIMANT_THRESHOLD * 2:
            score += 30
            signals.append(
                FraudSignal(
                    name="serial_claimant",
                    description=f"Serial claimant pattern: {previous_claims} previous claims",
                    weight=0.9,
                    category="history",
                )
            )
        elif previous_claims >= self.SERIAL_CLAIMANT_THRESHOLD:
            score += 15
            signals.append(
                FraudSignal(
                    name="multiple_claims",
                    description=f"Multiple previous claims: {previous_claims}",
                    weight=0.6,
                    category="history",
                )
            )

        return score, signals

    def _analyze_witnesses(self, data: Dict[str, Any]) -> tuple:
        """Analyze witness information"""
        signals = []
        score = 0

        witnesses = data.get("witnesses", 0)
        claim_amount = data.get("claim_amount", 0)

        # High-value claim with no witnesses
        if witnesses == 0 and claim_amount > 5000:
            score += 15
            signals.append(
                FraudSignal(
                    name="no_witnesses",
                    description="No witnesses for high-value claim",
                    weight=0.6,
                    category="verification",
                )
            )

        return score, signals

    def _analyze_description(self, data: Dict[str, Any]) -> tuple:
        """Analyze claim description for red flags"""
        signals = []
        score = 0

        description = data.get("description", "").lower()

        suspicious_count = sum(
            1 for keyword in self.SUSPICIOUS_DESCRIPTIONS if keyword in description
        )

        if suspicious_count >= 3:
            score += 15
            signals.append(
                FraudSignal(
                    name="suspicious_description",
                    description="Multiple high-risk keywords in claim description",
                    weight=0.6,
                    category="description",
                )
            )
        elif suspicious_count >= 1:
            score += 5
            signals.append(
                FraudSignal(
                    name="flagged_keywords",
                    description="Claim contains flagged keywords",
                    weight=0.3,
                    category="description",
                )
            )

        return score, signals

    def _generate_recommendation(
        self, score: float, signals: List[FraudSignal], data: Dict[str, Any]
    ) -> str:
        """Generate action recommendation"""
        claim_amount = data.get("claim_amount", 0)

        if score >= 80:
            return "DENY: High fraud probability. Refer to Special Investigations Unit (SIU)."
        elif score >= 60:
            return f"INVESTIGATE: Assign to fraud investigator. Request documentation and conduct field investigation."
        elif score >= 40:
            return "VERIFY: Conduct additional verification. Request supporting documents and witness statements."
        else:
            if claim_amount > self.HIGH_CLAIM_THRESHOLD:
                return "PROCESS: Low fraud indicators but high value. Standard review recommended."
            return "APPROVE: Claim appears legitimate. Process according to standard procedures."
