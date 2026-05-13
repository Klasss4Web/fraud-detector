"""
Transaction Fraud Detection Agent
==================================

Specialized agent for detecting financial transaction fraud patterns:
- Velocity attacks
- Unusual amounts
- Geographic anomalies
- Device/IP anomalies
- Time-based patterns
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult, FraudSignal, RiskLevel


class TransactionFraudAgent(BaseAgent):
    """Agent specialized in detecting transaction fraud"""

    # Thresholds for fraud detection
    VELOCITY_THRESHOLD = 10  # transactions per 24h
    HIGH_AMOUNT_THRESHOLD = 1000
    VERY_HIGH_AMOUNT_THRESHOLD = 5000
    AMOUNT_DEVIATION_FACTOR = 3  # times the average

    HIGH_RISK_LOCATIONS = [
        "Lagos, Nigeria",
        "Moscow, Russia",
        "Beijing, China",
        "Mumbai, India",
        "Romania",
        "Indonesia",
    ]

    HIGH_RISK_CATEGORIES = ["gift_cards", "wire_transfer", "crypto", "gambling"]

    def __init__(self):
        super().__init__("TransactionFraudAgent")

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """Analyze a transaction for fraud signals"""
        self.log(f"Analyzing transaction {data.get('transaction_id', 'unknown')}")

        signals = []
        risk_score = 0

        # 1. Velocity Analysis
        velocity_score, velocity_signals = self._analyze_velocity(data)
        risk_score += velocity_score
        signals.extend(velocity_signals)

        # 2. Amount Analysis
        amount_score, amount_signals = self._analyze_amount(data)
        risk_score += amount_score
        signals.extend(amount_signals)

        # 3. Location Analysis
        location_score, location_signals = self._analyze_location(data)
        risk_score += location_score
        signals.extend(location_signals)

        # 4. Device/IP Analysis
        device_score, device_signals = self._analyze_device(data)
        risk_score += device_score
        signals.extend(device_signals)

        # 5. Time Analysis
        time_score, time_signals = self._analyze_time(data)
        risk_score += time_score
        signals.extend(time_signals)

        # 6. Card-not-present risk
        if not data.get("card_present", True):
            risk_score += 10
            signals.append(
                FraudSignal(
                    name="card_not_present",
                    description="Transaction made without physical card",
                    weight=0.4,
                    category="transaction_type",
                )
            )

        # Generate recommendation
        recommendation = self._generate_recommendation(risk_score, signals)

        return self._create_result(
            entity_id=data.get("transaction_id", "unknown"),
            risk_score=risk_score,
            signals=signals,
            recommendation=recommendation,
            details={
                "amount": data.get("amount"),
                "merchant": data.get("merchant_name"),
                "location": data.get("location"),
                "velocity_24h": data.get("velocity_24h"),
            },
        )

    def _analyze_velocity(self, data: Dict[str, Any]) -> tuple:
        """Analyze transaction velocity patterns"""
        signals = []
        score = 0

        velocity = data.get("velocity_24h", 0)

        if velocity > self.VELOCITY_THRESHOLD * 2:
            score += 25
            signals.append(
                FraudSignal(
                    name="extreme_velocity",
                    description=f"Extremely high velocity: {velocity} transactions in 24h",
                    weight=0.9,
                    category="velocity",
                    evidence=f"Threshold: {self.VELOCITY_THRESHOLD}, Actual: {velocity}",
                )
            )
        elif velocity > self.VELOCITY_THRESHOLD:
            score += 15
            signals.append(
                FraudSignal(
                    name="high_velocity",
                    description=f"High transaction velocity: {velocity} in 24h",
                    weight=0.6,
                    category="velocity",
                    evidence=f"Threshold: {self.VELOCITY_THRESHOLD}, Actual: {velocity}",
                )
            )

        return score, signals

    def _analyze_amount(self, data: Dict[str, Any]) -> tuple:
        """Analyze transaction amount patterns"""
        signals = []
        score = 0

        amount = data.get("amount", 0)
        avg_amount = data.get("avg_amount_30d", 100)

        # Check for unusually high amounts
        if amount > self.VERY_HIGH_AMOUNT_THRESHOLD:
            score += 20
            signals.append(
                FraudSignal(
                    name="very_high_amount",
                    description=f"Very high transaction amount: ${amount:.2f}",
                    weight=0.8,
                    category="amount",
                )
            )
        elif amount > self.HIGH_AMOUNT_THRESHOLD:
            score += 10
            signals.append(
                FraudSignal(
                    name="high_amount",
                    description=f"High transaction amount: ${amount:.2f}",
                    weight=0.5,
                    category="amount",
                )
            )

        # Check deviation from average
        if avg_amount > 0 and amount > avg_amount * self.AMOUNT_DEVIATION_FACTOR:
            score += 15
            signals.append(
                FraudSignal(
                    name="amount_deviation",
                    description=f"Amount {amount / avg_amount:.1f}x higher than user average",
                    weight=0.7,
                    category="amount",
                    evidence=f"Average: ${avg_amount:.2f}, Current: ${amount:.2f}",
                )
            )

        return score, signals

    def _analyze_location(self, data: Dict[str, Any]) -> tuple:
        """Analyze geographic risk factors"""
        signals = []
        score = 0

        location = data.get("location", "")
        is_international = data.get("is_international", False)

        # Check high-risk locations
        for risky_loc in self.HIGH_RISK_LOCATIONS:
            if risky_loc.lower() in location.lower():
                score += 20
                signals.append(
                    FraudSignal(
                        name="high_risk_location",
                        description=f"Transaction from high-risk location: {location}",
                        weight=0.8,
                        category="location",
                    )
                )
                break

        # International transaction risk
        if is_international:
            score += 10
            signals.append(
                FraudSignal(
                    name="international_transaction",
                    description="International transaction detected",
                    weight=0.4,
                    category="location",
                )
            )

        return score, signals

    def _analyze_device(self, data: Dict[str, Any]) -> tuple:
        """Analyze device and IP patterns"""
        signals = []
        score = 0

        ip = data.get("ip_address", "")

        # Check for private/suspicious IP ranges
        if ip.startswith(("10.", "192.168.", "172.")):
            score += 15
            signals.append(
                FraudSignal(
                    name="suspicious_ip",
                    description="Transaction from private/VPN IP range",
                    weight=0.6,
                    category="device",
                )
            )

        return score, signals

    def _analyze_time(self, data: Dict[str, Any]) -> tuple:
        """Analyze time-based patterns"""
        signals = []
        score = 0

        timestamp = data.get("timestamp", "")

        # Check for unusual hours (simplified)
        if timestamp:
            try:
                hour = int(timestamp.split("T")[1].split(":")[0])
                if 2 <= hour <= 5:
                    score += 10
                    signals.append(
                        FraudSignal(
                            name="unusual_time",
                            description=f"Transaction at unusual hour: {hour}:00",
                            weight=0.4,
                            category="time",
                        )
                    )
            except (IndexError, ValueError):
                pass

        return score, signals

    def _generate_recommendation(self, score: float, signals: List[FraudSignal]) -> str:
        """Generate action recommendation based on analysis"""
        if score >= 80:
            return "BLOCK: High fraud probability. Decline transaction and alert security team."
        elif score >= 60:
            return (
                "CHALLENGE: Request additional verification (OTP, security questions)."
            )
        elif score >= 40:
            return "REVIEW: Flag for manual review within 24 hours."
        else:
            return "ALLOW: Transaction appears legitimate. Continue monitoring."
