"""
Test fixtures for fraud detection tests.
"""

import os
import pytest
from typing import Generator
from uuid import uuid4

# Set test environment before importing app modules
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # Use SQLite for unit tests
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from data.data_generator import SyntheticDataGenerator
from orchestrator import FraudDetectionOrchestrator
from db.models import Base, User, UserRole
from db.session import get_db
from auth import get_password_hash


# ============== Database Fixtures ==============


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine (SQLite in-memory)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create tables fresh for each test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    from api import app
    from api.routes import init_orchestrator
    from api.config import Settings

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Initialize orchestrator for tests
    settings = Settings(enable_llm=False)
    init_orchestrator(settings)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ============== Auth Fixtures ==============


@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session) -> User:
    """Create an admin user."""
    user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def analyst_user(db_session) -> User:
    """Create an analyst user."""
    user = User(
        email="analyst@example.com",
        hashed_password=get_password_hash("analystpassword123"),
        full_name="Analyst User",
        role=UserRole.ANALYST,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user) -> dict:
    """Get authorization headers for test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "testpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(client, admin_user) -> dict:
    """Get authorization headers for admin user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============== Data Generator Fixtures ==============


@pytest.fixture
def data_generator():
    """Create a data generator with fixed seed for reproducibility."""
    import random

    random.seed(42)  # Set seed for reproducibility
    return SyntheticDataGenerator(fraud_rate=0.3)


@pytest.fixture
def orchestrator():
    """Create an orchestrator without LLM for testing."""
    return FraudDetectionOrchestrator(
        enable_llm=False,
        auto_investigate_threshold=60.0,
    )


# ============== Sample Data Fixtures ==============


@pytest.fixture
def sample_transaction():
    """Create a sample transaction for testing."""
    return {
        "transaction_id": "TXN-TEST-001",
        "user_id": "USER-001",
        "amount": 150.00,
        "currency": "USD",
        "merchant_category": "electronics",
        "merchant_name": "Test Store",
        "location": "New York, US",
        "device_id": "DEV-001",
        "ip_address": "192.168.1.1",
        "timestamp": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def suspicious_transaction():
    """Create a suspicious transaction for testing."""
    return {
        "transaction_id": "TXN-SUS-001",
        "user_id": "USER-002",
        "amount": 9500.00,  # Very high amount
        "currency": "USD",
        "merchant_category": "gambling",  # High-risk category
        "merchant_name": "Casino Online",
        "location": "Nigeria",  # High-risk location
        "device_id": "DEV-002",
        "ip_address": "10.0.0.1",
        "timestamp": "2024-01-15T03:30:00Z",  # Unusual hour
    }


@pytest.fixture
def sample_insurance_claim():
    """Create a sample insurance claim for testing."""
    return {
        "claim_id": "CLM-TEST-001",
        "claimant_id": "CLMT-001",
        "claim_type": "auto",
        "claim_amount": 5000.00,
        "incident_date": "2024-01-10",
        "filing_date": "2024-01-12",
        "description": "Minor fender bender in parking lot",
        "policy_id": "POL-001",
        "witnesses": ["witness1@email.com"],
    }


@pytest.fixture
def suspicious_insurance_claim():
    """Create a suspicious insurance claim for testing."""
    return {
        "claim_id": "CLM-SUS-001",
        "claimant_id": "CLMT-002",
        "claim_type": "auto",
        "claim_amount": 95000.00,  # Very high amount
        "incident_date": "2024-01-10",
        "filing_date": "2024-01-10",  # Same day filing
        "description": "total loss whiplash injuries severe damage cash settlement needed",  # Suspicious keywords
        "policy_id": "POL-002",
        "witnesses": [],  # No witnesses
    }


@pytest.fixture
def sample_user_profile():
    """Create a sample user profile for testing."""
    return {
        "user_id": "USER-TEST-001",
        "email": "john.doe@gmail.com",
        "phone": "+1-555-123-4567",
        "account_age_days": 365,
        "device_count": 2,
        "login_frequency": 5.0,
        "failed_login_attempts": 0,
        "location_changes": 1,
    }


@pytest.fixture
def suspicious_user_profile():
    """Create a suspicious user profile for testing."""
    return {
        "user_id": "USER-SUS-001",
        "email": "random123@tempmail.xyz",  # Disposable email
        "phone": "+1-555-999-9999",
        "account_age_days": 2,  # Very new account
        "device_count": 15,  # Too many devices
        "login_frequency": 50.0,  # Very high login frequency
        "failed_login_attempts": 10,  # Many failed attempts
        "location_changes": 20,  # Many location changes
    }


@pytest.fixture
def sample_ecommerce_order():
    """Create a sample e-commerce order for testing."""
    return {
        "order_id": "ORD-TEST-001",
        "customer_id": "CUST-001",
        "order_total": 150.00,
        "item_count": 3,
        "shipping_address": "123 Main St, New York, NY 10001",
        "billing_address": "123 Main St, New York, NY 10001",
        "payment_method": "credit_card",
        "items": [
            {"name": "Book", "price": 25.00, "quantity": 2},
            {"name": "Pen Set", "price": 100.00, "quantity": 1},
        ],
        "is_expedited": False,
    }


@pytest.fixture
def suspicious_ecommerce_order():
    """Create a suspicious e-commerce order for testing."""
    return {
        "order_id": "ORD-SUS-001",
        "customer_id": "CUST-002",
        "order_total": 8500.00,  # Very high amount
        "item_count": 10,
        "shipping_address": "456 Oak Ave, Miami, FL 33101",  # Different from billing
        "billing_address": "789 Pine St, Los Angeles, CA 90001",
        "payment_method": "prepaid_card",  # Higher risk payment
        "items": [
            {"name": "iPhone 15 Pro", "price": 1200.00, "quantity": 5},
            {"name": "Gift Cards", "price": 500.00, "quantity": 5},  # High-risk items
        ],
        "is_expedited": True,  # Rush shipping
        "is_new_customer": True,
    }
