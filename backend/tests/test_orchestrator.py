"""
Tests for the Fraud Detection Orchestrator.
"""

import pytest
from orchestrator import (
    FraudDetectionOrchestrator,
    FraudAnalysisResult,
    EntityType,
)


class TestFraudDetectionOrchestrator:
    """Tests for FraudDetectionOrchestrator."""

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes correctly."""
        assert orchestrator is not None
        assert orchestrator.transaction_agent is not None
        assert orchestrator.insurance_agent is not None
        assert orchestrator.identity_agent is not None
        assert orchestrator.ecommerce_agent is not None
        assert orchestrator.risk_scorer is not None

    def test_orchestrator_without_llm(self):
        """Test orchestrator works without LLM."""
        orch = FraudDetectionOrchestrator(enable_llm=False)
        assert orch.investigation_agent is None

    def test_analyze_transaction(self, orchestrator, sample_transaction):
        """Test transaction analysis."""
        result = orchestrator.analyze_transaction(
            sample_transaction,
            auto_investigate=False,
        )

        assert isinstance(result, FraudAnalysisResult)
        assert result.entity_id == sample_transaction["transaction_id"]
        assert result.entity_type == "transaction"
        assert 0 <= result.risk_score <= 100
        assert result.risk_level in ["low", "medium", "high", "critical"]

    def test_analyze_suspicious_transaction(self, orchestrator, suspicious_transaction):
        """Test analysis of suspicious transaction returns higher risk."""
        result = orchestrator.analyze_transaction(
            suspicious_transaction,
            auto_investigate=False,
        )

        assert result.risk_score > 50
        assert len(result.signals) > 0

    def test_analyze_insurance_claim(self, orchestrator, sample_insurance_claim):
        """Test insurance claim analysis."""
        result = orchestrator.analyze_insurance_claim(
            sample_insurance_claim,
            auto_investigate=False,
        )

        assert isinstance(result, FraudAnalysisResult)
        assert result.entity_id == sample_insurance_claim["claim_id"]
        assert result.entity_type == "claim"

    def test_analyze_user_profile(self, orchestrator, sample_user_profile):
        """Test user profile analysis."""
        result = orchestrator.analyze_user_profile(
            sample_user_profile,
            auto_investigate=False,
        )

        assert isinstance(result, FraudAnalysisResult)
        assert result.entity_id == sample_user_profile["user_id"]
        assert result.entity_type == "profile"

    def test_analyze_ecommerce_order(self, orchestrator, sample_ecommerce_order):
        """Test e-commerce order analysis."""
        result = orchestrator.analyze_ecommerce_order(
            sample_ecommerce_order,
            auto_investigate=False,
        )

        assert isinstance(result, FraudAnalysisResult)
        assert result.entity_id == sample_ecommerce_order["order_id"]
        assert result.entity_type == "order"

    def test_analyze_comprehensive(self, orchestrator, sample_transaction, sample_user_profile):
        """Test comprehensive multi-source analysis."""
        result = orchestrator.analyze_comprehensive(
            transaction_data=sample_transaction,
            user_profile=sample_user_profile,
            auto_investigate=False,
        )

        assert isinstance(result, FraudAnalysisResult)
        assert result.entity_type == "comprehensive"
        assert len(result.agent_results) >= 2

    def test_analyze_comprehensive_requires_data(self, orchestrator):
        """Test that comprehensive analysis requires at least one data source."""
        with pytest.raises(ValueError):
            orchestrator.analyze_comprehensive(auto_investigate=False)

    def test_batch_analyze(self, orchestrator, data_generator):
        """Test batch analysis."""
        from dataclasses import asdict

        transactions = [asdict(data_generator.generate_transaction()) for _ in range(5)]

        results = orchestrator.batch_analyze(
            items=transactions,
            entity_type=EntityType.TRANSACTION,
            auto_investigate=False,
        )

        assert len(results) == 5
        # Results should be sorted by risk score (highest first)
        for i in range(len(results) - 1):
            assert results[i].risk_score >= results[i + 1].risk_score

    def test_get_high_risk_summary(self, orchestrator, data_generator):
        """Test high risk summary generation."""
        from dataclasses import asdict

        transactions = [asdict(data_generator.generate_transaction()) for _ in range(10)]

        results = orchestrator.batch_analyze(
            items=transactions,
            entity_type=EntityType.TRANSACTION,
            auto_investigate=False,
        )

        summary = orchestrator.get_high_risk_summary(results, threshold=60.0)

        assert "total_analyzed" in summary
        assert "high_risk_count" in summary
        assert "high_risk_rate" in summary
        assert "average_risk_score" in summary
        assert "risk_distribution" in summary
        assert summary["total_analyzed"] == 10


class TestFraudAnalysisResult:
    """Tests for FraudAnalysisResult dataclass."""

    def test_result_has_all_fields(self, orchestrator, sample_transaction):
        """Test that result contains all expected fields."""
        result = orchestrator.analyze_transaction(
            sample_transaction,
            auto_investigate=False,
        )

        assert hasattr(result, "entity_id")
        assert hasattr(result, "entity_type")
        assert hasattr(result, "risk_score")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "requires_action")
        assert hasattr(result, "recommendation")
        assert hasattr(result, "signals")
        assert hasattr(result, "agent_results")

    def test_signals_structure(self, orchestrator, suspicious_transaction):
        """Test that signals have correct structure."""
        result = orchestrator.analyze_transaction(
            suspicious_transaction,
            auto_investigate=False,
        )

        for signal in result.signals:
            assert "name" in signal
            assert "description" in signal
            assert "weight" in signal
            assert "category" in signal


class TestMixedDetectionAnalysis:
    """Tests for mixed detection analysis (legitimate + fraudulent transactions)."""

    def test_mixed_detection_analysis_basic(self, orchestrator):
        """Test basic mixed detection analysis works."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=5,
            num_fraudulent=5,
            use_llm=False,
        )

        assert "confusion_matrix" in result
        assert "metrics" in result
        assert "summary" in result
        assert "detailed_results" in result

    def test_confusion_matrix_counts(self, orchestrator):
        """Test confusion matrix counts sum correctly."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=5,
            num_fraudulent=5,
            use_llm=False,
        )

        cm = result["confusion_matrix"]
        total = (
            cm["true_positives"]
            + cm["true_negatives"]
            + cm["false_positives"]
            + cm["false_negatives"]
        )
        assert total == 10  # 5 legitimate + 5 fraudulent

    def test_metrics_are_valid(self, orchestrator):
        """Test that all metrics are in valid ranges."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=10,
            num_fraudulent=10,
            use_llm=False,
        )

        metrics = result["metrics"]

        # All metrics should be between 0 and 1
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1
        assert 0 <= metrics["specificity"] <= 1
        assert 0 <= metrics["false_positive_rate"] <= 1
        assert 0 <= metrics["false_negative_rate"] <= 1

    def test_summary_transaction_counts(self, orchestrator):
        """Test summary has correct transaction counts."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=7,
            num_fraudulent=3,
            use_llm=False,
        )

        summary = result["summary"]
        assert summary["total_transactions"] == 10
        assert summary["total_legitimate"] == 7
        assert summary["total_fraudulent"] == 3

    def test_detailed_results_structure(self, orchestrator):
        """Test detailed results have correct structure."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=3,
            num_fraudulent=3,
            use_llm=False,
        )

        for tx_result in result["detailed_results"]:
            assert "transaction_id" in tx_result
            assert "expected_fraud" in tx_result
            assert "predicted_fraud" in tx_result
            assert "risk_score" in tx_result
            assert "outcome" in tx_result
            assert tx_result["outcome"] in [
                "true_positive",
                "true_negative",
                "false_positive",
                "false_negative",
            ]

    def test_fraud_detection_effectiveness(self, orchestrator):
        """Test that the system detects fraud better than random."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=15,
            num_fraudulent=15,
            use_llm=False,
        )

        metrics = result["metrics"]

        # System should perform better than random (50% accuracy)
        # With well-designed fraud patterns, we expect high recall
        assert metrics["accuracy"] > 0.5, "System should perform better than random"

        # Fraudulent transactions should have higher average scores than legitimate
        summary = result["summary"]
        assert summary["score_separation"] > 0, (
            "Fraud scores should be higher than legitimate scores"
        )

    def test_interpretation_present(self, orchestrator):
        """Test that human-readable interpretations are present."""
        result = orchestrator.run_mixed_detection_analysis(
            num_legitimate=5,
            num_fraudulent=5,
            use_llm=False,
        )

        interpretation = result["interpretation"]
        assert "accuracy_meaning" in interpretation
        assert "precision_meaning" in interpretation
        assert "recall_meaning" in interpretation
        assert "f1_meaning" in interpretation
        assert "fpr_meaning" in interpretation
        assert "fnr_meaning" in interpretation
