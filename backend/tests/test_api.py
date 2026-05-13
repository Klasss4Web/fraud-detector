"""
Tests for the FastAPI REST API.
"""

import pytest
from fastapi.testclient import TestClient
from api import app
from api.routes import init_orchestrator
from api.config import Settings


@pytest.fixture(scope="module")
def client():
    """Create a test client."""
    # Initialize orchestrator for tests
    settings = Settings(enable_llm=False)
    init_orchestrator(settings)

    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "agents_loaded" in data
        assert len(data["agents_loaded"]) >= 5


class TestTransactionAnalysis:
    """Tests for transaction analysis endpoint."""

    def test_analyze_transaction_success(self, client, sample_transaction):
        """Test successful transaction analysis."""
        response = client.post(
            "/api/v1/analyze/transaction",
            json=sample_transaction,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == sample_transaction["transaction_id"]
        assert data["entity_type"] == "transaction"
        assert 0 <= data["risk_score"] <= 100
        assert data["risk_level"] in ["low", "medium", "high", "critical"]

    def test_analyze_suspicious_transaction(self, client, suspicious_transaction):
        """Test analysis of suspicious transaction."""
        response = client.post(
            "/api/v1/analyze/transaction",
            json=suspicious_transaction,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] > 50
        assert len(data["signals"]) > 0

    def test_analyze_transaction_invalid_data(self, client):
        """Test transaction analysis with invalid data."""
        response = client.post(
            "/api/v1/analyze/transaction",
            json={"invalid": "data"},
        )

        assert response.status_code == 422  # Validation error


class TestInsuranceClaimAnalysis:
    """Tests for insurance claim analysis endpoint."""

    def test_analyze_insurance_claim_success(self, client, sample_insurance_claim):
        """Test successful insurance claim analysis."""
        response = client.post(
            "/api/v1/analyze/insurance-claim",
            json=sample_insurance_claim,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == sample_insurance_claim["claim_id"]
        assert data["entity_type"] == "claim"


class TestUserProfileAnalysis:
    """Tests for user profile analysis endpoint."""

    def test_analyze_user_profile_success(self, client, sample_user_profile):
        """Test successful user profile analysis."""
        response = client.post(
            "/api/v1/analyze/user-profile",
            json=sample_user_profile,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == sample_user_profile["user_id"]
        assert data["entity_type"] == "profile"


class TestEcommerceOrderAnalysis:
    """Tests for e-commerce order analysis endpoint."""

    def test_analyze_ecommerce_order_success(self, client, sample_ecommerce_order):
        """Test successful e-commerce order analysis."""
        response = client.post(
            "/api/v1/analyze/ecommerce-order",
            json=sample_ecommerce_order,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == sample_ecommerce_order["order_id"]
        assert data["entity_type"] == "order"


class TestComprehensiveAnalysis:
    """Tests for comprehensive analysis endpoint."""

    def test_comprehensive_analysis_success(self, client, sample_transaction, sample_user_profile):
        """Test successful comprehensive analysis."""
        response = client.post(
            "/api/v1/analyze/comprehensive",
            json={
                "transaction": sample_transaction,
                "user_profile": sample_user_profile,
                "auto_investigate": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "comprehensive"
        assert len(data["agent_results"]) >= 2

    def test_comprehensive_analysis_requires_data(self, client):
        """Test that comprehensive analysis requires at least one data source."""
        response = client.post(
            "/api/v1/analyze/comprehensive",
            json={"auto_investigate": False},
        )

        # Should fail - either 400, 422, or 500 (internal error from ValueError)
        assert response.status_code >= 400


class TestBatchAnalysis:
    """Tests for batch analysis endpoint."""

    def test_batch_analysis_success(self, client, sample_transaction):
        """Test successful batch analysis."""
        transactions = [
            {**sample_transaction, "transaction_id": f"TXN-BATCH-{i}"} for i in range(3)
        ]

        response = client.post(
            "/api/v1/analyze/batch",
            json={
                "items": transactions,
                "entity_type": "transaction",
                "auto_investigate": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert "summary" in data
        assert data["summary"]["total_analyzed"] == 3
