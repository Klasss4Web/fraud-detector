"""
Tests for the database repository layer.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from db.models import (
    User,
    UserRole,
    Transaction,
    FraudAlert,
    Case,
    AlertStatus,
    CaseStatus,
    CaseResolution,
    RiskLevel,
    TransactionStatus,
)
from db.repository import (
    UserRepository,
    TransactionRepository,
    AlertRepository,
    CaseRepository,
    UserProfileRepository,
    AuditRepository,
)
from auth import get_password_hash


class TestUserRepository:
    """Tests for UserRepository."""

    def test_create_user(self, db_session):
        """Test creating a new user."""
        repo = UserRepository(db_session)

        user = repo.create_user(
            email="repo_test@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Repo Test User",
            role=UserRole.VIEWER,
        )

        assert user.id is not None
        assert user.email == "repo_test@example.com"
        assert user.full_name == "Repo Test User"
        assert user.role == UserRole.VIEWER
        assert user.is_active is True

    def test_get_by_id(self, db_session, test_user):
        """Test getting user by ID."""
        repo = UserRepository(db_session)

        found = repo.get_by_id(test_user.id)

        assert found is not None
        assert found.id == test_user.id
        assert found.email == test_user.email

    def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent user by ID."""
        repo = UserRepository(db_session)

        found = repo.get_by_id(uuid4())

        assert found is None

    def test_get_by_email(self, db_session, test_user):
        """Test getting user by email."""
        repo = UserRepository(db_session)

        found = repo.get_by_email("testuser@example.com")

        assert found is not None
        assert found.id == test_user.id

    def test_get_by_email_not_found(self, db_session):
        """Test getting non-existent user by email."""
        repo = UserRepository(db_session)

        found = repo.get_by_email("nonexistent@example.com")

        assert found is None

    def test_get_active_analysts(self, db_session, analyst_user):
        """Test getting active analysts."""
        repo = UserRepository(db_session)

        analysts = repo.get_active_analysts()

        assert len(analysts) >= 1
        assert any(a.email == "analyst@example.com" for a in analysts)

    def test_update_last_login(self, db_session, test_user):
        """Test updating last login timestamp."""
        repo = UserRepository(db_session)

        assert test_user.last_login_at is None

        repo.update_last_login(test_user.id)
        db_session.refresh(test_user)

        assert test_user.last_login_at is not None

    def test_create_api_key(self, db_session, test_user):
        """Test creating an API key."""
        repo = UserRepository(db_session)

        api_key = repo.create_api_key(
            user_id=test_user.id,
            key_hash="hashed_key_value",
            key_prefix="fd_test",
            name="Test Key",
            scopes=["read:transactions"],
        )

        assert api_key.id is not None
        assert api_key.user_id == test_user.id
        assert api_key.name == "Test Key"

    def test_get_api_key_by_hash(self, db_session, test_user):
        """Test getting API key by hash."""
        repo = UserRepository(db_session)

        repo.create_api_key(
            user_id=test_user.id,
            key_hash="unique_hash_123",
            key_prefix="fd_test",
            name="Findable Key",
            scopes=["read:transactions"],
        )

        found = repo.get_api_key_by_hash("unique_hash_123")

        assert found is not None
        assert found.name == "Findable Key"


class TestTransactionRepository:
    """Tests for TransactionRepository."""

    def test_create_transaction(self, db_session):
        """Test creating a transaction."""
        repo = TransactionRepository(db_session)

        txn = repo.create(
            {
                "external_id": "TXN-001",
                "customer_id": "CUST-001",
                "amount": 100.50,
                "currency": "USD",
                "merchant_name": "Test Merchant",
                "merchant_category": "retail",
                "location": "New York, US",
                "device_id": "DEV-001",
                "ip_address": "192.168.1.1",
            }
        )

        assert txn.id is not None
        assert txn.external_id == "TXN-001"
        assert txn.amount == 100.50

    def test_get_by_external_id(self, db_session):
        """Test getting transaction by external ID."""
        repo = TransactionRepository(db_session)

        repo.create(
            {
                "external_id": "TXN-FIND-001",
                "customer_id": "CUST-001",
                "amount": 50.00,
                "currency": "USD",
            }
        )

        found = repo.get_by_external_id("TXN-FIND-001")

        assert found is not None
        assert found.external_id == "TXN-FIND-001"

    def test_get_customer_transactions(self, db_session):
        """Test getting recent transactions for a customer."""
        repo = TransactionRepository(db_session)

        # Create multiple transactions
        for i in range(5):
            repo.create(
                {
                    "external_id": f"TXN-CUST-{i}",
                    "customer_id": "CUST-MULTI",
                    "amount": 10.00 * (i + 1),
                    "currency": "USD",
                }
            )

        transactions = repo.get_customer_transactions("CUST-MULTI", hours=24)

        assert len(transactions) == 5

    def test_get_customer_stats(self, db_session):
        """Test getting aggregated customer stats."""
        repo = TransactionRepository(db_session)

        # Create transactions with known amounts
        for amount in [100.0, 200.0, 300.0]:
            repo.create(
                {
                    "external_id": f"TXN-STATS-{amount}",
                    "customer_id": "CUST-STATS",
                    "amount": amount,
                    "currency": "USD",
                }
            )

        stats = repo.get_customer_stats("CUST-STATS", days=30)

        assert stats["transaction_count"] == 3
        assert stats["total_amount"] == 600.0
        assert stats["avg_amount"] == 200.0
        assert stats["max_amount"] == 300.0

    def test_get_velocity(self, db_session):
        """Test getting velocity metrics."""
        repo = TransactionRepository(db_session)

        # Create transactions for velocity check
        for i in range(3):
            repo.create(
                {
                    "external_id": f"TXN-VEL-{i}",
                    "customer_id": "CUST-VEL",
                    "amount": 50.0,
                    "currency": "USD",
                    "merchant_name": f"Merchant-{i}",
                    "location": f"Location-{i}",
                }
            )

        velocity = repo.get_velocity("customer", "CUST-VEL", hours=1)

        assert velocity["count"] == 3
        assert velocity["total_amount"] == 150.0
        assert velocity["unique_merchants"] == 3

    def test_update_status(self, db_session):
        """Test updating transaction status."""
        repo = TransactionRepository(db_session)

        txn = repo.create(
            {
                "external_id": "TXN-STATUS",
                "customer_id": "CUST-001",
                "amount": 100.0,
                "currency": "USD",
            }
        )

        repo.update_status(
            txn.id,
            status=TransactionStatus.FLAGGED,
            risk_score=75.0,
            risk_level=RiskLevel.HIGH,
        )
        db_session.refresh(txn)

        assert txn.status == TransactionStatus.FLAGGED
        assert txn.risk_score == 75.0
        assert txn.risk_level == RiskLevel.HIGH


class TestAlertRepository:
    """Tests for AlertRepository."""

    def _create_transaction(self, db_session, external_id="TXN-ALERT"):
        """Helper to create a transaction for alerts."""
        repo = TransactionRepository(db_session)
        return repo.create(
            {
                "external_id": external_id,
                "customer_id": "CUST-001",
                "amount": 100.0,
                "currency": "USD",
            }
        )

    def test_create_alert(self, db_session):
        """Test creating a fraud alert."""
        txn = self._create_transaction(db_session)
        repo = AlertRepository(db_session)

        alert = repo.create(
            {
                "transaction_id": txn.id,
                "alert_type": "high_amount",
                "severity": RiskLevel.HIGH,
                "risk_score": 85.0,
                "description": "Unusually high transaction amount",
                "signals": {"amount_zscore": 3.5},
            }
        )

        assert alert.id is not None
        assert alert.alert_type == "high_amount"
        assert alert.severity == RiskLevel.HIGH

    def test_get_pending_alerts(self, db_session):
        """Test getting pending alerts."""
        txn = self._create_transaction(db_session, "TXN-PENDING")
        repo = AlertRepository(db_session)

        repo.create(
            {
                "transaction_id": txn.id,
                "alert_type": "test",
                "severity": RiskLevel.MEDIUM,
                "risk_score": 60.0,
                "status": AlertStatus.NEW,
            }
        )

        pending = repo.get_pending_alerts()

        assert len(pending) >= 1

    def test_resolve_alert(self, db_session, test_user):
        """Test resolving an alert."""
        txn = self._create_transaction(db_session, "TXN-RESOLVE")
        repo = AlertRepository(db_session)

        alert = repo.create(
            {
                "transaction_id": txn.id,
                "alert_type": "test",
                "severity": RiskLevel.LOW,
                "risk_score": 30.0,
            }
        )

        repo.resolve_alert(
            alert_id=alert.id,
            resolved_by=test_user.id,
            status=AlertStatus.DISMISSED,
            notes="False positive",
            actual_outcome="false_positive",
        )
        db_session.refresh(alert)

        assert alert.status == AlertStatus.DISMISSED
        assert alert.resolved_by == test_user.id
        assert alert.actual_outcome == "false_positive"

    def test_record_chargeback(self, db_session):
        """Test recording a chargeback."""
        txn = self._create_transaction(db_session, "TXN-CHARGEBACK")
        repo = AlertRepository(db_session)

        alert = repo.create(
            {
                "transaction_id": txn.id,
                "alert_type": "test",
                "severity": RiskLevel.HIGH,
                "risk_score": 80.0,
            }
        )

        repo.record_chargeback(alert.id, amount=100.0)
        db_session.refresh(alert)

        assert alert.chargeback_received is True
        assert alert.chargeback_amount == 100.0


class TestCaseRepository:
    """Tests for CaseRepository."""

    def test_create_case(self, db_session):
        """Test creating a case."""
        repo = CaseRepository(db_session)

        case = repo.create(
            title="Test Investigation",
            case_type="transaction_fraud",
            description="Testing case creation",
            priority=2,
        )

        assert case.id is not None
        assert case.case_number.startswith("CASE-")
        assert case.title == "Test Investigation"
        assert case.status == CaseStatus.OPEN

    def test_case_number_generation(self, db_session):
        """Test that case numbers are unique and sequential."""
        repo = CaseRepository(db_session)

        case1 = repo.create(title="Case 1", case_type="test", priority=2)
        case2 = repo.create(title="Case 2", case_type="test", priority=2)

        # Both should have unique case numbers
        assert case1.case_number != case2.case_number

        # Should be sequential
        num1 = int(case1.case_number.split("-")[-1])
        num2 = int(case2.case_number.split("-")[-1])
        assert num2 == num1 + 1

    def test_assign_case(self, db_session, analyst_user):
        """Test assigning a case to an analyst."""
        repo = CaseRepository(db_session)

        case = repo.create(title="Assign Test", case_type="test", priority=2)

        repo.assign_case(case.id, analyst_user.id)
        db_session.refresh(case)

        assert case.assigned_to == analyst_user.id
        assert case.status == CaseStatus.ASSIGNED

    def test_get_open_cases(self, db_session):
        """Test getting open cases."""
        repo = CaseRepository(db_session)

        repo.create(title="Open Case 1", case_type="test", priority=1)
        repo.create(title="Open Case 2", case_type="test", priority=2)

        open_cases = repo.get_open_cases()

        assert len(open_cases) >= 2

    def test_resolve_case(self, db_session):
        """Test resolving a case."""
        repo = CaseRepository(db_session)

        case = repo.create(title="To Resolve", case_type="test", priority=2)

        repo.resolve_case(
            case.id,
            resolution=CaseResolution.CONFIRMED_FRAUD,
            confirmed_fraud_amount=500.0,
            prevented_amount=500.0,
        )
        db_session.refresh(case)

        assert case.status == CaseStatus.RESOLVED
        assert case.resolution == CaseResolution.CONFIRMED_FRAUD
        assert case.confirmed_fraud_amount == 500.0

    def test_add_case_note(self, db_session, analyst_user):
        """Test adding a note to a case."""
        repo = CaseRepository(db_session)

        case = repo.create(title="Note Test", case_type="test", priority=2)

        note = repo.add_note(
            case_id=case.id,
            author_id=analyst_user.id,
            content="Investigation notes here",
            note_type="investigation",
        )

        assert note.id is not None
        assert note.content == "Investigation notes here"

    def test_sla_calculation(self, db_session):
        """Test that SLA is calculated based on priority."""
        repo = CaseRepository(db_session)

        # Priority 1 = 2 hours SLA
        high_priority_case = repo.create(title="Urgent", case_type="test", priority=1)

        # Priority 4 = 72 hours SLA
        low_priority_case = repo.create(title="Low Priority", case_type="test", priority=4)

        # High priority should have earlier SLA
        assert high_priority_case.sla_due_at < low_priority_case.sla_due_at


class TestUserProfileRepository:
    """Tests for UserProfileRepository."""

    def test_get_or_create_new(self, db_session):
        """Test creating a new user profile."""
        repo = UserProfileRepository(db_session)

        profile = repo.get_or_create("NEW-CUSTOMER-001")

        assert profile.customer_id == "NEW-CUSTOMER-001"

    def test_get_or_create_existing(self, db_session):
        """Test getting existing user profile."""
        repo = UserProfileRepository(db_session)

        # Create first
        profile1 = repo.get_or_create("EXISTING-CUSTOMER")
        # Get again
        profile2 = repo.get_or_create("EXISTING-CUSTOMER")

        assert profile1.id == profile2.id

    def test_update_baseline(self, db_session):
        """Test updating customer baseline."""
        repo = UserProfileRepository(db_session)

        profile = repo.get_or_create("BASELINE-CUSTOMER")

        repo.update_baseline(
            customer_id="BASELINE-CUSTOMER",
            avg_amount=150.0,
            max_amount=500.0,
            transaction_count=50,
            avg_per_day=2.5,
        )
        db_session.refresh(profile)

        assert profile.avg_transaction_amount_30d == 150.0
        assert profile.max_transaction_amount_30d == 500.0

    def test_update_last_location(self, db_session):
        """Test updating last location."""
        repo = UserProfileRepository(db_session)

        profile = repo.get_or_create("LOCATION-CUSTOMER")
        now = datetime.utcnow()

        repo.update_last_location(
            customer_id="LOCATION-CUSTOMER",
            location="New York, US",
            lat=40.7128,
            lon=-74.0060,
            timestamp=now,
        )
        db_session.refresh(profile)

        assert profile.last_transaction_location == "New York, US"
        assert profile.last_transaction_lat == 40.7128


class TestAuditRepository:
    """Tests for AuditRepository."""

    def test_log_action(self, db_session, test_user):
        """Test logging an audit action."""
        repo = AuditRepository(db_session)

        log = repo.log(
            action="user.login",
            user_id=test_user.id,
            resource_type="session",
            ip_address="192.168.1.1",
            user_agent="Test Agent",
        )

        assert log.id is not None
        assert log.action == "user.login"
        assert log.checksum is not None  # Integrity check

    def test_get_logs_filtered(self, db_session, test_user):
        """Test getting filtered audit logs."""
        repo = AuditRepository(db_session)

        # Create some logs
        repo.log(action="user.login", user_id=test_user.id)
        repo.log(action="user.logout", user_id=test_user.id)
        repo.log(action="case.create", user_id=test_user.id)

        # Filter by action
        login_logs = repo.get_logs(action="user.login")

        assert all(log.action == "user.login" for log in login_logs)

    def test_log_with_old_new_values(self, db_session, test_user):
        """Test logging with change tracking."""
        repo = AuditRepository(db_session)

        log = repo.log(
            action="case.update",
            user_id=test_user.id,
            resource_type="case",
            resource_id=uuid4(),
            old_values={"status": "open"},
            new_values={"status": "resolved"},
        )

        assert log.old_values == {"status": "open"}
        assert log.new_values == {"status": "resolved"}
