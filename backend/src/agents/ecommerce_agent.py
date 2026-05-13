"""
E-commerce Fraud Detection Agent
=================================

Specialized agent for detecting e-commerce fraud:
- Reseller fraud
- Stolen credit card usage
- Friendly fraud (chargeback abuse)
- Account fraud
"""

from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentResult, FraudSignal


class EcommerceFraudAgent(BaseAgent):
    """Agent specialized in detecting e-commerce fraud"""

    # Thresholds
    HIGH_ORDER_THRESHOLD = 500
    VERY_HIGH_ORDER_THRESHOLD = 2000
    CHARGEBACK_THRESHOLD = 2

    HIGH_RISK_CATEGORIES = ["Electronics", "Gift Cards", "Jewelry", "Designer Items"]

    def __init__(self):
        super().__init__("EcommerceFraudAgent")

    def analyze(self, data: Dict[str, Any]) -> AgentResult:
        """Analyze an e-commerce order for fraud signals"""
        self.log(f"Analyzing order {data.get('order_id', 'unknown')}")

        signals = []
        risk_score = 0

        # 1. Order Value Analysis
        value_score, value_signals = self._analyze_order_value(data)
        risk_score += value_score
        signals.extend(value_signals)

        # 2. Item Risk Analysis
        item_score, item_signals = self._analyze_items(data)
        risk_score += item_score
        signals.extend(item_signals)

        # 3. Address Analysis
        address_score, address_signals = self._analyze_addresses(data)
        risk_score += address_score
        signals.extend(address_signals)

        # 4. Customer Profile
        customer_score, customer_signals = self._analyze_customer(data)
        risk_score += customer_score
        signals.extend(customer_signals)

        # 5. Shipping Patterns
        shipping_score, shipping_signals = self._analyze_shipping(data)
        risk_score += shipping_score
        signals.extend(shipping_signals)

        # 6. Chargeback History
        chargeback_score, chargeback_signals = self._analyze_chargebacks(data)
        risk_score += chargeback_score
        signals.extend(chargeback_signals)

        # Determine fraud type
        fraud_type = self._determine_fraud_type(signals, data)

        recommendation = self._generate_recommendation(risk_score, fraud_type, data)

        return self._create_result(
            entity_id=data.get("order_id", "unknown"),
            risk_score=risk_score,
            signals=signals,
            recommendation=recommendation,
            details={
                "total_amount": data.get("total_amount"),
                "item_count": len(data.get("items", [])),
                "is_new_customer": data.get("is_new_customer"),
                "suspected_fraud_type": fraud_type,
            },
        )

    def _analyze_order_value(self, data: Dict[str, Any]) -> tuple:
        """Analyze order value for risk"""
        signals = []
        score = 0

        total = data.get("total_amount", 0)

        if total > self.VERY_HIGH_ORDER_THRESHOLD:
            score += 20
            signals.append(
                FraudSignal(
                    name="very_high_order",
                    description=f"Very high order value: ${total:,.2f}",
                    weight=0.7,
                    category="value",
                )
            )
        elif total > self.HIGH_ORDER_THRESHOLD:
            score += 10
            signals.append(
                FraudSignal(
                    name="high_order",
                    description=f"High order value: ${total:,.2f}",
                    weight=0.4,
                    category="value",
                )
            )

        return score, signals

    def _analyze_items(self, data: Dict[str, Any]) -> tuple:
        """Analyze ordered items for risk"""
        signals = []
        score = 0

        items = data.get("items", [])
        high_risk_items = data.get("high_risk_items", False)

        # Check for high-risk categories
        if high_risk_items:
            score += 15
            signals.append(
                FraudSignal(
                    name="high_risk_items",
                    description="Order contains high-risk items (electronics, gift cards, jewelry)",
                    weight=0.6,
                    category="items",
                )
            )

        # Check for bulk orders
        total_quantity = sum(item.get("quantity", 1) for item in items)
        if total_quantity > 5:
            score += 15
            signals.append(
                FraudSignal(
                    name="bulk_order",
                    description=f"Bulk order: {total_quantity} items",
                    weight=0.5,
                    category="items",
                )
            )

        # Check for multiple high-value items of same category
        categories = [item.get("category") for item in items]
        for category in set(categories):
            if (
                categories.count(category) >= 3
                and category in self.HIGH_RISK_CATEGORIES
            ):
                score += 15
                signals.append(
                    FraudSignal(
                        name="multiple_same_category",
                        description=f"Multiple {category} items in order",
                        weight=0.6,
                        category="items",
                    )
                )
                break

        return score, signals

    def _analyze_addresses(self, data: Dict[str, Any]) -> tuple:
        """Analyze shipping/billing address patterns"""
        signals = []
        score = 0

        shipping_billing_match = data.get("shipping_billing_match", True)

        if not shipping_billing_match:
            score += 15
            signals.append(
                FraudSignal(
                    name="address_mismatch",
                    description="Shipping and billing addresses do not match",
                    weight=0.5,
                    category="address",
                )
            )

        return score, signals

    def _analyze_customer(self, data: Dict[str, Any]) -> tuple:
        """Analyze customer profile risk"""
        signals = []
        score = 0

        is_new_customer = data.get("is_new_customer", False)
        total = data.get("total_amount", 0)

        # New customer with high-value order
        if is_new_customer:
            score += 10
            signals.append(
                FraudSignal(
                    name="new_customer",
                    description="First-time customer",
                    weight=0.3,
                    category="customer",
                )
            )

            if total > self.HIGH_ORDER_THRESHOLD:
                score += 10
                signals.append(
                    FraudSignal(
                        name="new_customer_high_value",
                        description="High-value order from new customer",
                        weight=0.5,
                        category="customer",
                    )
                )

        return score, signals

    def _analyze_shipping(self, data: Dict[str, Any]) -> tuple:
        """Analyze shipping patterns"""
        signals = []
        score = 0

        express_shipping = data.get("express_shipping", False)
        is_new_customer = data.get("is_new_customer", False)
        high_risk_items = data.get("high_risk_items", False)

        # Express shipping with risk factors
        if express_shipping and (is_new_customer or high_risk_items):
            score += 15
            signals.append(
                FraudSignal(
                    name="express_shipping_risk",
                    description="Express shipping combined with other risk factors",
                    weight=0.5,
                    category="shipping",
                )
            )

        return score, signals

    def _analyze_chargebacks(self, data: Dict[str, Any]) -> tuple:
        """Analyze chargeback history"""
        signals = []
        score = 0

        previous_chargebacks = data.get("previous_chargebacks", 0)

        if previous_chargebacks > self.CHARGEBACK_THRESHOLD * 2:
            score += 35
            signals.append(
                FraudSignal(
                    name="serial_chargebacker",
                    description=f"Serial chargeback history: {previous_chargebacks} previous chargebacks",
                    weight=0.95,
                    category="chargeback",
                )
            )
        elif previous_chargebacks > self.CHARGEBACK_THRESHOLD:
            score += 25
            signals.append(
                FraudSignal(
                    name="chargeback_history",
                    description=f"Chargeback history: {previous_chargebacks} previous chargebacks",
                    weight=0.8,
                    category="chargeback",
                )
            )
        elif previous_chargebacks > 0:
            score += 10
            signals.append(
                FraudSignal(
                    name="prior_chargeback",
                    description=f"Prior chargeback on record",
                    weight=0.4,
                    category="chargeback",
                )
            )

        return score, signals

    def _determine_fraud_type(
        self, signals: List[FraudSignal], data: Dict[str, Any]
    ) -> str:
        """Determine the most likely fraud type"""
        signal_names = [s.name for s in signals]

        if (
            "serial_chargebacker" in signal_names
            or "chargeback_history" in signal_names
        ):
            return "friendly_fraud"
        elif "bulk_order" in signal_names and "high_risk_items" in signal_names:
            return "reseller_fraud"
        elif "new_customer" in signal_names and "address_mismatch" in signal_names:
            return "stolen_card"
        elif len(signals) > 3:
            return "general_fraud"
        else:
            return "low_risk"

    def _generate_recommendation(
        self, score: float, fraud_type: str, data: Dict[str, Any]
    ) -> str:
        """Generate action recommendation"""
        total = data.get("total_amount", 0)

        if score >= 80:
            return f"REJECT: High probability of {fraud_type}. Decline order and blacklist if appropriate."
        elif score >= 60:
            return f"REVIEW: Suspected {fraud_type}. Manual review required before shipping."
        elif score >= 40:
            return f"VERIFY: Potential {fraud_type} indicators. Require phone verification or additional authentication."
        else:
            if total > self.VERY_HIGH_ORDER_THRESHOLD:
                return "PROCESS: Low risk but high value. Standard verification recommended."
            return "APPROVE: Order appears legitimate. Process normally."
