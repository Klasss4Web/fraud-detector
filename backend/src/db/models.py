"""
SQLAlchemy models for the fraud detection system.
Uses PostgreSQL as the primary database.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    ForeignKey,
    Enum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


# ============== Enums ==============


class UserRole(str, PyEnum):
    """User roles for RBAC"""

    VIEWER = "viewer"
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    ADMIN = "admin"
    API_CLIENT = "api_client"


class AlertStatus(str, PyEnum):
    """Status of a fraud alert"""

    NEW = "new"
    REVIEWING = "reviewing"
    ESCALATED = "escalated"
    CONFIRMED_FRAUD = "confirmed_fraud"
    FALSE_POSITIVE = "false_positive"
    CLOSED = "closed"


class CaseStatus(str, PyEnum):
    """Status of an investigation case"""

    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_INFO = "pending_info"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CaseResolution(str, PyEnum):
    """Resolution of a case"""

    CONFIRMED_FRAUD = "confirmed_fraud"
    FALSE_POSITIVE = "false_positive"
    INCONCLUSIVE = "inconclusive"
    DUPLICATE = "duplicate"


class RiskLevel(str, PyEnum):
    """Risk classification levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransactionStatus(str, PyEnum):
    """Transaction decision status"""

    APPROVED = "approved"
    DECLINED = "declined"
    CHALLENGED = "challenged"  # Sent to MFA/verification
    PENDING_REVIEW = "pending_review"


# ============== User & Authentication Models ==============


class User(Base):
    """System users (analysts, admins)"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Analyst-specific fields
    max_cases = Column(Integer, default=20)  # Max concurrent cases
    specializations = Column(ARRAY(String), default=[])  # e.g., ["velocity", "identity"]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    assigned_cases = relationship(
        "Case", back_populates="assigned_to_user", foreign_keys="Case.assigned_to"
    )
    case_notes = relationship("CaseNote", back_populates="author")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (Index("ix_users_role_active", "role", "is_active"),)


class APIKey(Base):
    """API keys for programmatic access"""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)  # SHA256 hash of key
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    name = Column(String(100), nullable=False)  # Friendly name

    # Scopes define what this key can do
    scopes = Column(ARRAY(String), default=["read:alerts"])

    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_prefix", "key_prefix"),
        Index("ix_api_keys_active", "is_active", "expires_at"),
    )


# ============== Transaction & Alert Models ==============


class Transaction(Base):
    """Processed transactions"""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(
        String(100), unique=True, nullable=False, index=True
    )  # Client's transaction ID

    # Transaction details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    merchant_category = Column(String(50))
    merchant_name = Column(String(255))
    merchant_id = Column(String(100))

    # Location info
    location = Column(String(255))
    country_code = Column(String(2))
    latitude = Column(Float)
    longitude = Column(Float)

    # Device/Network info
    device_id = Column(String(255), index=True)
    ip_address = Column(INET)
    user_agent = Column(Text)

    # User info
    customer_id = Column(String(100), nullable=False, index=True)
    card_last_four = Column(String(4))
    card_type = Column(String(20))  # visa, mastercard, etc.
    card_present = Column(Boolean, default=False)

    # Risk assessment
    risk_score = Column(Float)
    risk_level = Column(Enum(RiskLevel))
    status = Column(Enum(TransactionStatus), default=TransactionStatus.APPROVED)

    # Timing
    transaction_time = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_time_ms = Column(Integer)  # How long analysis took

    # Raw data and signals
    raw_data = Column(JSONB)  # Original request payload
    signals = Column(JSONB)  # Detected fraud signals
    agent_scores = Column(JSONB)  # Individual agent scores

    # Relationships
    alerts = relationship("FraudAlert", back_populates="transaction")

    __table_args__ = (
        Index("ix_transactions_customer_time", "customer_id", "transaction_time"),
        Index("ix_transactions_device_time", "device_id", "transaction_time"),
        Index("ix_transactions_risk", "risk_level", "status"),
        Index("ix_transactions_time", "transaction_time"),
    )


class FraudAlert(Base):
    """Fraud alerts requiring review"""

    __tablename__ = "fraud_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)

    # Alert details
    alert_type = Column(String(50), nullable=False)  # velocity, high_amount, etc.
    severity = Column(Enum(RiskLevel), nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.NEW)

    risk_score = Column(Float, nullable=False)
    confidence = Column(Float, default=0.8)

    # Detection info
    triggered_rules = Column(ARRAY(String))  # Which rules triggered this
    signals = Column(JSONB)  # Detailed signals

    # LLM investigation (if performed)
    llm_analysis = Column(Text)
    llm_recommendation = Column(String(50))

    # Resolution
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolution_notes = Column(Text)

    # Outcome tracking
    actual_outcome = Column(String(50))  # confirmed_fraud, false_positive, etc.
    chargeback_received = Column(Boolean, default=False)
    chargeback_amount = Column(Float)
    chargeback_date = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    transaction = relationship("Transaction", back_populates="alerts")
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"))
    case = relationship("Case", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_status_severity", "status", "severity"),
        Index("ix_alerts_created", "created_at"),
        Index("ix_alerts_type", "alert_type"),
    )


# ============== Case Management Models ==============


class Case(Base):
    """Investigation cases (can contain multiple alerts)"""

    __tablename__ = "cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(20), unique=True, nullable=False)  # Human-readable: CASE-2024-00001

    # Case details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    case_type = Column(String(50))  # velocity_attack, identity_fraud, etc.
    priority = Column(Integer, default=2)  # 1=Critical, 2=High, 3=Medium, 4=Low

    status = Column(Enum(CaseStatus), default=CaseStatus.OPEN)
    resolution = Column(Enum(CaseResolution))

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assigned_at = Column(DateTime(timezone=True))

    # SLA tracking
    sla_due_at = Column(DateTime(timezone=True))
    sla_breached = Column(Boolean, default=False)

    # Financial impact
    total_amount_at_risk = Column(Float, default=0.0)
    confirmed_fraud_amount = Column(Float, default=0.0)
    prevented_amount = Column(Float, default=0.0)

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))

    # Metadata
    tags = Column(ARRAY(String), default=[])

    # Relationships
    alerts = relationship("FraudAlert", back_populates="case")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")
    assigned_to_user = relationship(
        "User", back_populates="assigned_cases", foreign_keys=[assigned_to]
    )

    __table_args__ = (
        Index("ix_cases_status_priority", "status", "priority"),
        Index("ix_cases_assigned", "assigned_to", "status"),
        Index("ix_cases_sla", "sla_due_at", "sla_breached"),
    )


class CaseNote(Base):
    """Notes/comments on investigation cases"""

    __tablename__ = "case_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)
    note_type = Column(String(50), default="comment")  # comment, evidence, decision, escalation

    # For evidence attachments
    attachments = Column(JSONB)  # [{filename, url, mime_type}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    case = relationship("Case", back_populates="notes")
    author = relationship("User", back_populates="case_notes")


# ============== User Behavior Models ==============


class UserProfile(Base):
    """Customer profiles with behavioral baselines"""

    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(100), unique=True, nullable=False, index=True)

    # Account info
    email = Column(String(255))
    email_domain = Column(String(100))
    email_risk_score = Column(Float)
    phone = Column(String(50))
    account_created_at = Column(DateTime(timezone=True))

    # Behavioral baselines (updated periodically)
    avg_transaction_amount_30d = Column(Float, default=0.0)
    max_transaction_amount_30d = Column(Float, default=0.0)
    transaction_count_30d = Column(Integer, default=0)
    avg_transactions_per_day = Column(Float, default=0.0)

    # Typical patterns
    typical_locations = Column(ARRAY(String), default=[])
    typical_merchants = Column(ARRAY(String), default=[])
    typical_hours = Column(JSONB)  # {0: 0.01, 1: 0.005, ..., 23: 0.08}
    typical_device_ids = Column(ARRAY(String), default=[])

    # Risk indicators
    risk_score = Column(Float, default=0.0)
    previous_fraud_count = Column(Integer, default=0)
    chargeback_count = Column(Integer, default=0)

    # Last known location (for impossible travel)
    last_transaction_location = Column(String(255))
    last_transaction_lat = Column(Float)
    last_transaction_lon = Column(Float)
    last_transaction_time = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (Index("ix_user_profiles_risk", "risk_score"),)


class DeviceFingerprint(Base):
    """Device fingerprints and their risk scores"""

    __tablename__ = "device_fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), unique=True, nullable=False, index=True)

    # Device info
    device_type = Column(String(50))  # mobile, desktop, tablet
    os = Column(String(50))
    browser = Column(String(50))
    screen_resolution = Column(String(20))
    timezone = Column(String(50))
    language = Column(String(10))

    # Risk assessment
    risk_score = Column(Float, default=0.0)
    is_emulator = Column(Boolean, default=False)
    is_rooted = Column(Boolean, default=False)
    is_vpn = Column(Boolean, default=False)

    # Association
    associated_customer_ids = Column(ARRAY(String), default=[])
    associated_ip_addresses = Column(ARRAY(INET), default=[])

    # History
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True))
    transaction_count = Column(Integer, default=0)
    fraud_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VelocityRecord(Base):
    """Real-time velocity tracking (also cached in Redis)"""

    __tablename__ = "velocity_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # What we're tracking
    entity_type = Column(String(20), nullable=False)  # customer, device, card, ip
    entity_id = Column(String(255), nullable=False)

    # Time window
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    window_type = Column(String(10), nullable=False)  # 1h, 6h, 24h, 7d

    # Counts
    transaction_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    decline_count = Column(Integer, default=0)
    unique_merchants = Column(Integer, default=0)
    unique_locations = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_velocity_entity", "entity_type", "entity_id", "window_type"),
        Index("ix_velocity_window", "window_start", "window_end"),
        UniqueConstraint(
            "entity_type", "entity_id", "window_type", "window_start", name="uq_velocity_record"
        ),
    )


# ============== Audit & Compliance ==============


class AuditLog(Base):
    """Immutable audit log for compliance"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"))
    ip_address = Column(INET)
    user_agent = Column(Text)

    # What
    action = Column(String(100), nullable=False)  # e.g., "alert.resolve", "case.assign"
    resource_type = Column(String(50))  # transaction, alert, case, user
    resource_id = Column(UUID(as_uuid=True))

    # Details
    old_values = Column(JSONB)  # Previous state
    new_values = Column(JSONB)  # New state
    extra_data = Column(JSONB)  # Additional context (renamed from metadata)

    # Integrity
    checksum = Column(String(64))  # SHA256 of log entry for integrity verification

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_action", "action", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
        Index("ix_audit_user", "user_id", "created_at"),
        Index("ix_audit_time", "created_at"),
    )


# ============== Observability & Metrics ==============


class MetricSnapshot(Base):
    """
    Periodic snapshots of system metrics.
    Stored every minute/hour for historical tracking.
    """

    __tablename__ = "metric_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Time bucket
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # "minute", "hour", "day"

    # Alert metrics
    alerts_received = Column(Integer, default=0)
    alerts_processed = Column(Integer, default=0)

    # Decision metrics
    decisions_total = Column(Integer, default=0)
    decisions_allow = Column(Integer, default=0)
    decisions_block = Column(Integer, default=0)
    decisions_review = Column(Integer, default=0)

    # Escalation metrics
    escalations_total = Column(Integer, default=0)
    escalations_pending = Column(Integer, default=0)

    # Performance metrics
    avg_processing_time_ms = Column(Float, default=0.0)

    # Risk score distribution
    risk_scores = Column(JSONB)  # {"low": 10, "medium": 5, "high": 3, "critical": 1}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_metric_time_granularity", "timestamp", "granularity"),
        UniqueConstraint("timestamp", "granularity", name="uq_metric_snapshot"),
    )


class AgentPerformance(Base):
    """
    Agent performance metrics over time.
    """

    __tablename__ = "agent_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Time bucket
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # "hour", "day"

    # Agent info
    agent_name = Column(String(100), nullable=False, index=True)

    # Execution metrics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)

    # Timing
    total_execution_time_ms = Column(Float, default=0.0)
    min_execution_time_ms = Column(Float)
    max_execution_time_ms = Column(Float)
    avg_execution_time_ms = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_agent_perf_time", "agent_name", "timestamp"),
        UniqueConstraint("timestamp", "granularity", "agent_name", name="uq_agent_performance"),
    )


class EvaluationOutcomeType(str, PyEnum):
    """Outcome of fraud detection evaluation"""

    TRUE_POSITIVE = "true_positive"
    TRUE_NEGATIVE = "true_negative"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"


class EvaluationRecord(Base):
    """
    Records of prediction outcomes for model evaluation.
    Used to calculate confusion matrix and accuracy metrics.
    """

    __tablename__ = "evaluation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reference
    prediction_id = Column(String(100), index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)

    # Prediction details
    predicted_action = Column(String(50), nullable=False)  # allow, block, review
    predicted_risk_score = Column(Float, nullable=False)
    predicted_confidence = Column(Float)
    model_name = Column(String(100))
    model_version = Column(String(50))

    # Actual outcome (filled when feedback received)
    actual_outcome = Column(Enum(EvaluationOutcomeType))
    human_decision = Column(String(50))  # What the analyst decided
    feedback_source = Column(String(50))  # human_review, chargeback, customer
    feedback_received_at = Column(DateTime(timezone=True))

    # Notes
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_eval_entity", "entity_type", "entity_id"),
        Index("ix_eval_outcome", "actual_outcome", "created_at"),
        Index("ix_eval_time", "created_at"),
    )


class ConfusionMatrixSnapshot(Base):
    """
    Periodic snapshots of confusion matrix for tracking model performance over time.
    """

    __tablename__ = "confusion_matrix_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Time bucket
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # "hour", "day", "week"

    # Optional filter
    entity_type = Column(String(50))  # null = overall
    model_name = Column(String(100))  # null = all models

    # Confusion matrix values
    true_positives = Column(Integer, default=0)
    true_negatives = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)

    # Calculated metrics
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    accuracy = Column(Float)

    # Total evaluated in this period
    total_evaluated = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_confusion_time", "timestamp", "granularity"),
        UniqueConstraint(
            "timestamp", "granularity", "entity_type", "model_name", name="uq_confusion_snapshot"
        ),
    )


class LLMUsageRecord(Base):
    """
    Records of individual LLM API calls for cost and usage tracking.
    """

    __tablename__ = "llm_usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Call identification
    call_id = Column(String(100), unique=True, index=True)

    # Model info
    model = Column(String(100), nullable=False, index=True)
    provider = Column(String(50))  # openai, openrouter, anthropic

    # Token usage
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    # Cost (in USD)
    input_cost = Column(Float, default=0.0)
    output_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)

    # Performance
    latency_ms = Column(Float)
    success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Context
    agent_name = Column(String(100), index=True)
    operation = Column(String(100))  # analyze, recommend, investigate
    entity_id = Column(String(255))

    # Request/Response metadata (optional, for debugging)
    request_metadata = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_llm_model_time", "model", "created_at"),
        Index("ix_llm_agent_time", "agent_name", "created_at"),
    )


class LLMUsageSummary(Base):
    """
    Aggregated LLM usage summaries for reporting.
    Pre-computed for faster dashboard queries.
    """

    __tablename__ = "llm_usage_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Time bucket
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # "hour", "day"

    # Optional grouping
    model = Column(String(100))  # null = all models
    agent_name = Column(String(100))  # null = all agents

    # Aggregated metrics
    total_calls = Column(Integer, default=0)
    successful_calls = Column(Integer, default=0)
    failed_calls = Column(Integer, default=0)

    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    total_cost = Column(Float, default=0.0)

    avg_latency_ms = Column(Float)
    min_latency_ms = Column(Float)
    max_latency_ms = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_llm_summary_time", "timestamp", "granularity"),
        UniqueConstraint("timestamp", "granularity", "model", "agent_name", name="uq_llm_summary"),
    )
