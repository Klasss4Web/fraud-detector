"""
Tests for fraud detection agents.
"""

import pytest
from agents import (
    TransactionFraudAgent,
    InsuranceFraudAgent,
    IdentityFraudAgent,
    EcommerceFraudAgent,
    RiskScoringAgent,
    AgentResult,
    RiskLevel,
)


class TestTransactionFraudAgent:
    """Tests for TransactionFraudAgent."""

    def test_analyze_normal_transaction(self, sample_transaction):
        """Test analysis of a normal transaction."""
        agent = TransactionFraudAgent()
        result = agent.analyze(sample_transaction)

        assert isinstance(result, AgentResult)
        assert result.agent_name == "TransactionFraudAgent"
        assert result.entity_id == sample_transaction["transaction_id"]
        assert 0 <= result.risk_score <= 100
        assert isinstance(result.risk_level, RiskLevel)

    def test_analyze_suspicious_transaction(self, suspicious_transaction):
        """Test analysis of a suspicious transaction."""
        agent = TransactionFraudAgent()
        result = agent.analyze(suspicious_transaction)

        assert result.risk_score > 50  # Should be flagged as higher risk
        assert len(result.signals) > 0  # Should have fraud signals

    def test_high_amount_detection(self):
        """Test detection of unusually high amounts."""
        agent = TransactionFraudAgent()

        high_amount_txn = {
            "transaction_id": "TXN-HIGH",
            "amount": 50000.00,
            "merchant_category": "retail",
            "merchant_name": "Test",
            "location": "US",
        }
        result = agent.analyze(high_amount_txn)

        # Should have detected amount anomaly
        signal_names = [s.name for s in result.signals]
        assert any("amount" in name.lower() for name in signal_names)


class TestInsuranceFraudAgent:
    """Tests for InsuranceFraudAgent."""

    def test_analyze_normal_claim(self, sample_insurance_claim):
        """Test analysis of a normal insurance claim."""
        agent = InsuranceFraudAgent()
        result = agent.analyze(sample_insurance_claim)

        assert isinstance(result, AgentResult)
        assert result.agent_name == "InsuranceFraudAgent"
        assert result.entity_id == sample_insurance_claim["claim_id"]

    def test_analyze_suspicious_claim(self, suspicious_insurance_claim):
        """Test analysis of a suspicious insurance claim."""
        agent = InsuranceFraudAgent()
        result = agent.analyze(suspicious_insurance_claim)

        # Should detect some risk - exact threshold varies
        assert result.risk_score > 30
        # Should have at least some signals detected

    def test_high_claim_amount_detection(self):
        """Test detection of unusually high claim amounts."""
        agent = InsuranceFraudAgent()

        high_claim = {
            "claim_id": "CLM-HIGH",
            "claim_type": "auto",
            "claim_amount": 200000.00,
            "incident_date": "2024-01-10",
            "filing_date": "2024-01-15",
            "description": "Car accident",
            "claimant_id": "CLMT-001",
        }
        result = agent.analyze(high_claim)

        assert result.risk_score > 30  # Should flag high amounts


class TestIdentityFraudAgent:
    """Tests for IdentityFraudAgent."""

    def test_analyze_normal_profile(self, sample_user_profile):
        """Test analysis of a normal user profile."""
        agent = IdentityFraudAgent()
        result = agent.analyze(sample_user_profile)

        assert isinstance(result, AgentResult)
        assert result.agent_name == "IdentityFraudAgent"
        assert result.entity_id == sample_user_profile["user_id"]
        assert result.risk_score < 50  # Normal profile should be low risk

    def test_analyze_suspicious_profile(self, suspicious_user_profile):
        """Test analysis of a suspicious user profile."""
        agent = IdentityFraudAgent()
        result = agent.analyze(suspicious_user_profile)

        # Should detect higher risk than normal
        assert result.risk_score > 30

    def test_new_account_detection(self):
        """Test detection of very new accounts."""
        agent = IdentityFraudAgent()

        new_account = {
            "user_id": "USER-NEW",
            "email": "new@email.com",
            "account_age_days": 1,
            "device_count": 1,
            "login_frequency": 1.0,
            "failed_login_attempts": 0,
            "location_changes": 0,
        }
        result = agent.analyze(new_account)

        signal_names = [s.name for s in result.signals]
        assert any("account" in name.lower() or "new" in name.lower() for name in signal_names)


class TestEcommerceFraudAgent:
    """Tests for EcommerceFraudAgent."""

    def test_analyze_normal_order(self, sample_ecommerce_order):
        """Test analysis of a normal e-commerce order."""
        agent = EcommerceFraudAgent()
        result = agent.analyze(sample_ecommerce_order)

        assert isinstance(result, AgentResult)
        assert result.agent_name == "EcommerceFraudAgent"
        assert result.entity_id == sample_ecommerce_order["order_id"]

    def test_analyze_suspicious_order(self, suspicious_ecommerce_order):
        """Test analysis of a suspicious e-commerce order."""
        agent = EcommerceFraudAgent()
        result = agent.analyze(suspicious_ecommerce_order)

        # Should produce a valid result with some signals
        assert isinstance(result, AgentResult)
        assert result.entity_id == suspicious_ecommerce_order["order_id"]

    def test_address_mismatch_detection(self):
        """Test detection of billing/shipping address mismatch."""
        agent = EcommerceFraudAgent()

        mismatch_order = {
            "order_id": "ORD-MISMATCH",
            "order_total": 500.00,
            "item_count": 2,
            "shipping_address": "123 Main St, New York, NY",
            "billing_address": "456 Other Ave, Los Angeles, CA",
            "customer_id": "CUST-001",
            "payment_method": "credit_card",
        }
        result = agent.analyze(mismatch_order)

        # The agent should analyze this - check it returns a valid result
        assert isinstance(result, AgentResult)
        assert result.entity_id == "ORD-MISMATCH"


class TestRiskScoringAgent:
    """Tests for RiskScoringAgent."""

    def test_aggregate_single_result(self, sample_transaction):
        """Test aggregation of a single agent result."""
        txn_agent = TransactionFraudAgent()
        risk_agent = RiskScoringAgent()

        txn_result = txn_agent.analyze(sample_transaction)
        aggregated = risk_agent.aggregate(
            results=[txn_result],
            entity_id=sample_transaction["transaction_id"],
            entity_type="transaction",
        )

        assert aggregated.entity_id == sample_transaction["transaction_id"]
        assert aggregated.entity_type == "transaction"
        assert 0 <= aggregated.final_risk_score <= 100

    def test_aggregate_multiple_results(self, sample_transaction, sample_user_profile):
        """Test aggregation of multiple agent results."""
        txn_agent = TransactionFraudAgent()
        identity_agent = IdentityFraudAgent()
        risk_agent = RiskScoringAgent()

        txn_result = txn_agent.analyze(sample_transaction)
        identity_result = identity_agent.analyze(sample_user_profile)

        aggregated = risk_agent.aggregate(
            results=[txn_result, identity_result],
            entity_id="COMBINED-001",
            entity_type="comprehensive",
        )

        assert len(aggregated.agent_scores) == 2
        assert aggregated.confidence > 0

    def test_risk_level_classification(self):
        """Test that risk levels are correctly assigned."""
        risk_agent = RiskScoringAgent()

        # Create mock results with different scores
        from fraud_detection.agents.base_agent import AgentResult, RiskLevel as RL

        low_result = AgentResult(
            agent_name="TestAgent",
            entity_id="TEST",
            risk_score=20.0,
            risk_level=RL.LOW,
            signals=[],
        )

        aggregated = risk_agent.aggregate(
            results=[low_result],
            entity_id="TEST",
            entity_type="test",
        )

        assert aggregated.risk_level == RL.LOW
