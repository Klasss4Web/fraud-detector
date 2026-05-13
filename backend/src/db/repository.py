"""
Repository pattern for database operations.
Provides clean data access abstractions.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from .models import (
    User,
    APIKey,
    Transaction,
    FraudAlert,
    Case,
    CaseNote,
    UserProfile,
    DeviceFingerprint,
    VelocityRecord,
    AuditLog,
    AlertStatus,
    CaseStatus,
    CaseResolution,
    RiskLevel,
    TransactionStatus,
    UserRole,
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()


class UserRepository(BaseRepository):
    """Repository for user and API key operations."""

    def create_user(
        self, email: str, hashed_password: str, full_name: str, role: UserRole = UserRole.VIEWER
    ) -> User:
        """Create a new user."""
        user = User(email=email, hashed_password=hashed_password, full_name=full_name, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_active_analysts(self) -> List[User]:
        """Get all active analysts for case assignment."""
        return (
            self.db.query(User)
            .filter(
                User.is_active == True, User.role.in_([UserRole.ANALYST, UserRole.SENIOR_ANALYST])
            )
            .all()
        )

    def get_analyst_workload(self, user_id: UUID) -> int:
        """Get count of open cases assigned to an analyst."""
        return (
            self.db.query(Case)
            .filter(
                Case.assigned_to == user_id,
                Case.status.in_([CaseStatus.OPEN, CaseStatus.ASSIGNED, CaseStatus.IN_PROGRESS]),
            )
            .count()
        )

    def update_last_login(self, user_id: UUID):
        """Update user's last login timestamp."""
        self.db.query(User).filter(User.id == user_id).update({"last_login_at": datetime.utcnow()})
        self.db.commit()

    # API Key operations
    def create_api_key(
        self,
        user_id: UUID,
        key_hash: str,
        key_prefix: str,
        name: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None,
    ) -> APIKey:
        """Create a new API key."""
        api_key = APIKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=scopes,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by its hash."""
        return (
            self.db.query(APIKey)
            .filter(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
                or_(APIKey.expires_at == None, APIKey.expires_at > datetime.utcnow()),
            )
            .first()
        )

    def update_api_key_last_used(self, key_id: UUID):
        """Update API key's last used timestamp."""
        self.db.query(APIKey).filter(APIKey.id == key_id).update(
            {"last_used_at": datetime.utcnow()}
        )
        self.db.commit()


class TransactionRepository(BaseRepository):
    """Repository for transaction operations."""

    def create(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Create a new transaction record."""
        transaction = Transaction(**transaction_data)
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID."""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_by_external_id(self, external_id: str) -> Optional[Transaction]:
        """Get transaction by external ID."""
        return self.db.query(Transaction).filter(Transaction.external_id == external_id).first()

    def get_customer_transactions(
        self, customer_id: str, hours: int = 24, limit: int = 100
    ) -> List[Transaction]:
        """Get recent transactions for a customer."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(Transaction)
            .filter(Transaction.customer_id == customer_id, Transaction.transaction_time >= since)
            .order_by(desc(Transaction.transaction_time))
            .limit(limit)
            .all()
        )

    def get_device_transactions(
        self, device_id: str, hours: int = 24, limit: int = 100
    ) -> List[Transaction]:
        """Get recent transactions for a device."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(Transaction)
            .filter(Transaction.device_id == device_id, Transaction.transaction_time >= since)
            .order_by(desc(Transaction.transaction_time))
            .limit(limit)
            .all()
        )

    def get_customer_stats(self, customer_id: str, days: int = 30) -> Dict[str, Any]:
        """Get aggregated stats for a customer."""
        since = datetime.utcnow() - timedelta(days=days)

        result = (
            self.db.query(
                func.count(Transaction.id).label("count"),
                func.avg(Transaction.amount).label("avg_amount"),
                func.max(Transaction.amount).label("max_amount"),
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(Transaction.customer_id == customer_id, Transaction.transaction_time >= since)
            .first()
        )

        return {
            "transaction_count": result.count or 0,
            "avg_amount": float(result.avg_amount or 0),
            "max_amount": float(result.max_amount or 0),
            "total_amount": float(result.total_amount or 0),
        }

    def get_velocity(self, entity_type: str, entity_id: str, hours: int) -> Dict[str, Any]:
        """Get velocity metrics for an entity."""
        since = datetime.utcnow() - timedelta(hours=hours)

        if entity_type == "customer":
            filter_col = Transaction.customer_id
        elif entity_type == "device":
            filter_col = Transaction.device_id
        else:
            filter_col = Transaction.customer_id

        result = (
            self.db.query(
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total_amount"),
                func.count(func.distinct(Transaction.merchant_name)).label("unique_merchants"),
                func.count(func.distinct(Transaction.location)).label("unique_locations"),
            )
            .filter(filter_col == entity_id, Transaction.transaction_time >= since)
            .first()
        )

        return {
            "count": result.count or 0,
            "total_amount": float(result.total_amount or 0),
            "unique_merchants": result.unique_merchants or 0,
            "unique_locations": result.unique_locations or 0,
        }

    def update_status(
        self,
        transaction_id: UUID,
        status: TransactionStatus,
        risk_score: float = None,
        risk_level: RiskLevel = None,
    ):
        """Update transaction status and risk assessment."""
        updates = {"status": status}
        if risk_score is not None:
            updates["risk_score"] = risk_score
        if risk_level is not None:
            updates["risk_level"] = risk_level

        self.db.query(Transaction).filter(Transaction.id == transaction_id).update(updates)
        self.db.commit()


class AlertRepository(BaseRepository):
    """Repository for fraud alert operations."""

    def create(self, alert_data: Dict[str, Any]) -> FraudAlert:
        """Create a new fraud alert."""
        alert = FraudAlert(**alert_data)
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_by_id(self, alert_id: UUID) -> Optional[FraudAlert]:
        """Get alert by ID."""
        return self.db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()

    def get_pending_alerts(self, severity: RiskLevel = None, limit: int = 50) -> List[FraudAlert]:
        """Get pending alerts requiring review."""
        query = self.db.query(FraudAlert).filter(
            FraudAlert.status.in_([AlertStatus.NEW, AlertStatus.REVIEWING])
        )

        if severity:
            query = query.filter(FraudAlert.severity == severity)

        return query.order_by(desc(FraudAlert.severity), FraudAlert.created_at).limit(limit).all()

    def get_alerts_by_status(
        self, status: AlertStatus, since: datetime = None, limit: int = 100
    ) -> List[FraudAlert]:
        """Get alerts by status."""
        query = self.db.query(FraudAlert).filter(FraudAlert.status == status)

        if since:
            query = query.filter(FraudAlert.created_at >= since)

        return query.order_by(desc(FraudAlert.created_at)).limit(limit).all()

    def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: UUID,
        status: AlertStatus,
        notes: str = None,
        actual_outcome: str = None,
    ):
        """Resolve a fraud alert."""
        updates = {
            "status": status,
            "resolved_by": resolved_by,
            "resolved_at": datetime.utcnow(),
            "resolution_notes": notes,
            "actual_outcome": actual_outcome,
        }

        self.db.query(FraudAlert).filter(FraudAlert.id == alert_id).update(updates)
        self.db.commit()

    def record_chargeback(self, alert_id: UUID, amount: float, chargeback_date: datetime = None):
        """Record a chargeback for an alert."""
        self.db.query(FraudAlert).filter(FraudAlert.id == alert_id).update(
            {
                "chargeback_received": True,
                "chargeback_amount": amount,
                "chargeback_date": chargeback_date or datetime.utcnow(),
                "actual_outcome": "confirmed_fraud",
            }
        )
        self.db.commit()

    def get_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get alert metrics for dashboard."""
        since = datetime.utcnow() - timedelta(days=days)

        total = (
            self.db.query(func.count(FraudAlert.id)).filter(FraudAlert.created_at >= since).scalar()
        )

        by_status = dict(
            self.db.query(FraudAlert.status, func.count(FraudAlert.id))
            .filter(FraudAlert.created_at >= since)
            .group_by(FraudAlert.status)
            .all()
        )

        confirmed_fraud = (
            self.db.query(func.count(FraudAlert.id))
            .filter(FraudAlert.created_at >= since, FraudAlert.actual_outcome == "confirmed_fraud")
            .scalar()
        )

        false_positives = (
            self.db.query(func.count(FraudAlert.id))
            .filter(FraudAlert.created_at >= since, FraudAlert.actual_outcome == "false_positive")
            .scalar()
        )

        return {
            "total_alerts": total,
            "by_status": {str(k): v for k, v in by_status.items()},
            "confirmed_fraud": confirmed_fraud,
            "false_positives": false_positives,
            "precision": confirmed_fraud / (confirmed_fraud + false_positives)
            if (confirmed_fraud + false_positives) > 0
            else 0,
        }


class CaseRepository(BaseRepository):
    """Repository for case management operations."""

    def _generate_case_number(self) -> str:
        """Generate a unique case number."""
        year = datetime.utcnow().year

        # Get the last case number for this year
        last_case = (
            self.db.query(Case)
            .filter(Case.case_number.like(f"CASE-{year}-%"))
            .order_by(desc(Case.case_number))
            .first()
        )

        if last_case:
            last_num = int(last_case.case_number.split("-")[-1])
            new_num = last_num + 1
        else:
            new_num = 1

        return f"CASE-{year}-{new_num:05d}"

    def create(
        self,
        title: str,
        case_type: str,
        alert_ids: List[UUID] = None,
        description: str = None,
        priority: int = 2,
    ) -> Case:
        """Create a new investigation case."""
        # Calculate SLA based on priority
        sla_hours = {1: 2, 2: 8, 3: 24, 4: 72}
        sla_due = datetime.utcnow() + timedelta(hours=sla_hours.get(priority, 24))

        case = Case(
            case_number=self._generate_case_number(),
            title=title,
            description=description,
            case_type=case_type,
            priority=priority,
            sla_due_at=sla_due,
        )
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)

        # Link alerts to case
        if alert_ids:
            self.db.query(FraudAlert).filter(FraudAlert.id.in_(alert_ids)).update(
                {"case_id": case.id}, synchronize_session=False
            )

            # Calculate total amount at risk
            total_amount = (
                self.db.query(func.sum(Transaction.amount))
                .join(FraudAlert, FraudAlert.transaction_id == Transaction.id)
                .filter(FraudAlert.case_id == case.id)
                .scalar()
            )

            case.total_amount_at_risk = total_amount or 0.0
            self.db.commit()

        return case

    def get_by_id(self, case_id: UUID) -> Optional[Case]:
        """Get case by ID."""
        return self.db.query(Case).filter(Case.id == case_id).first()

    def get_by_case_number(self, case_number: str) -> Optional[Case]:
        """Get case by case number."""
        return self.db.query(Case).filter(Case.case_number == case_number).first()

    def get_open_cases(
        self, assigned_to: UUID = None, priority: int = None, limit: int = 50
    ) -> List[Case]:
        """Get open cases."""
        query = self.db.query(Case).filter(
            Case.status.in_([CaseStatus.OPEN, CaseStatus.ASSIGNED, CaseStatus.IN_PROGRESS])
        )

        if assigned_to:
            query = query.filter(Case.assigned_to == assigned_to)
        if priority:
            query = query.filter(Case.priority == priority)

        return query.order_by(Case.priority, Case.sla_due_at).limit(limit).all()

    def assign_case(self, case_id: UUID, user_id: UUID):
        """Assign a case to an analyst."""
        self.db.query(Case).filter(Case.id == case_id).update(
            {
                "assigned_to": user_id,
                "assigned_at": datetime.utcnow(),
                "status": CaseStatus.ASSIGNED,
            }
        )
        self.db.commit()

    def update_status(self, case_id: UUID, status: CaseStatus):
        """Update case status."""
        updates = {"status": status}
        if status == CaseStatus.RESOLVED:
            updates["resolved_at"] = datetime.utcnow()

        self.db.query(Case).filter(Case.id == case_id).update(updates)
        self.db.commit()

    def resolve_case(
        self,
        case_id: UUID,
        resolution: CaseResolution,
        confirmed_fraud_amount: float = 0.0,
        prevented_amount: float = 0.0,
    ):
        """Resolve a case."""
        self.db.query(Case).filter(Case.id == case_id).update(
            {
                "status": CaseStatus.RESOLVED,
                "resolution": resolution,
                "resolved_at": datetime.utcnow(),
                "confirmed_fraud_amount": confirmed_fraud_amount,
                "prevented_amount": prevented_amount,
            }
        )
        self.db.commit()

    def add_note(
        self, case_id: UUID, author_id: UUID, content: str, note_type: str = "comment"
    ) -> CaseNote:
        """Add a note to a case."""
        note = CaseNote(case_id=case_id, author_id=author_id, content=content, note_type=note_type)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get_sla_breached_cases(self) -> List[Case]:
        """Get cases that have breached their SLA."""
        return (
            self.db.query(Case)
            .filter(
                Case.status.in_([CaseStatus.OPEN, CaseStatus.ASSIGNED, CaseStatus.IN_PROGRESS]),
                Case.sla_due_at < datetime.utcnow(),
                Case.sla_breached == False,
            )
            .all()
        )

    def mark_sla_breached(self, case_ids: List[UUID]):
        """Mark cases as SLA breached."""
        self.db.query(Case).filter(Case.id.in_(case_ids)).update(
            {"sla_breached": True}, synchronize_session=False
        )
        self.db.commit()


class VelocityRepository(BaseRepository):
    """Repository for velocity tracking (works alongside Redis cache)."""

    def record_velocity(
        self,
        entity_type: str,
        entity_id: str,
        window_type: str,
        amount: float,
        merchant: str = None,
    ):
        """Record a velocity event (used for persistence, Redis is primary)."""
        # Calculate window boundaries
        now = datetime.utcnow()
        window_hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
        hours = window_hours.get(window_type, 24)

        window_start = now.replace(minute=0, second=0, microsecond=0)
        if window_type == "7d":
            window_start = window_start.replace(hour=0)

        window_end = window_start + timedelta(hours=hours)

        # Upsert velocity record
        existing = (
            self.db.query(VelocityRecord)
            .filter(
                VelocityRecord.entity_type == entity_type,
                VelocityRecord.entity_id == entity_id,
                VelocityRecord.window_type == window_type,
                VelocityRecord.window_start == window_start,
            )
            .first()
        )

        if existing:
            existing.transaction_count += 1
            existing.total_amount += amount
            if merchant:
                existing.unique_merchants += 1  # Simplified; ideally track unique
        else:
            record = VelocityRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                window_type=window_type,
                window_start=window_start,
                window_end=window_end,
                transaction_count=1,
                total_amount=amount,
                unique_merchants=1 if merchant else 0,
            )
            self.db.add(record)

        self.db.commit()


class UserProfileRepository(BaseRepository):
    """Repository for customer profile operations."""

    def get_or_create(self, customer_id: str) -> UserProfile:
        """Get or create a user profile."""
        profile = self.db.query(UserProfile).filter(UserProfile.customer_id == customer_id).first()

        if not profile:
            profile = UserProfile(customer_id=customer_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

        return profile

    def update_baseline(
        self,
        customer_id: str,
        avg_amount: float,
        max_amount: float,
        transaction_count: int,
        avg_per_day: float,
    ):
        """Update customer's behavioral baseline."""
        self.db.query(UserProfile).filter(UserProfile.customer_id == customer_id).update(
            {
                "avg_transaction_amount_30d": avg_amount,
                "max_transaction_amount_30d": max_amount,
                "transaction_count_30d": transaction_count,
                "avg_transactions_per_day": avg_per_day,
                "updated_at": datetime.utcnow(),
            }
        )
        self.db.commit()

    def update_last_location(
        self, customer_id: str, location: str, lat: float, lon: float, timestamp: datetime
    ):
        """Update customer's last known location."""
        self.db.query(UserProfile).filter(UserProfile.customer_id == customer_id).update(
            {
                "last_transaction_location": location,
                "last_transaction_lat": lat,
                "last_transaction_lon": lon,
                "last_transaction_time": timestamp,
            }
        )
        self.db.commit()

    def get_last_location(self, customer_id: str) -> Optional[Tuple[str, float, float, datetime]]:
        """Get customer's last known location for impossible travel detection."""
        profile = self.db.query(UserProfile).filter(UserProfile.customer_id == customer_id).first()

        if profile and profile.last_transaction_lat:
            return (
                profile.last_transaction_location,
                profile.last_transaction_lat,
                profile.last_transaction_lon,
                profile.last_transaction_time,
            )
        return None


class AuditRepository(BaseRepository):
    """Repository for audit log operations."""

    def log(
        self,
        action: str,
        user_id: UUID = None,
        api_key_id: UUID = None,
        resource_type: str = None,
        resource_id: UUID = None,
        old_values: Dict = None,
        new_values: Dict = None,
        ip_address: str = None,
        user_agent: str = None,
        extra_data: Dict = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        import hashlib
        import json

        # Create checksum for integrity
        log_data = {
            "action": action,
            "user_id": str(user_id) if user_id else None,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
        checksum = hashlib.sha256(json.dumps(log_data, sort_keys=True).encode()).hexdigest()

        audit_log = AuditLog(
            user_id=user_id,
            api_key_id=api_key_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
            checksum=checksum,
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log

    def get_logs(
        self,
        user_id: UUID = None,
        action: str = None,
        resource_type: str = None,
        since: datetime = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs with filters."""
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if since:
            query = query.filter(AuditLog.created_at >= since)

        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
