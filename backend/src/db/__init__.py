"""
Database package for fraud detection system.
Provides PostgreSQL persistence and Redis caching.

Both are OPTIONAL - the system works without them:
- Without PostgreSQL: Data is not persisted (in-memory only)
- Without Redis: Uses in-memory cache (still works, just not distributed)
"""

# Session management (always available - provides fallbacks)
from .session import (
    get_db,
    get_redis,
    init_db,
    close_db,
    DatabaseSession,
    RedisCache,
    check_database_health,
    check_redis_health,
    SQLALCHEMY_AVAILABLE,
    REDIS_AVAILABLE,
)

# Models and repositories (only if SQLAlchemy is available)
try:
    from .models import (
        Base,
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
    )
    from .repository import (
        TransactionRepository,
        AlertRepository,
        CaseRepository,
        UserRepository,
        VelocityRepository,
    )

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Provide None placeholders
    Base = None
    User = None
    APIKey = None
    Transaction = None
    FraudAlert = None
    Case = None
    CaseNote = None
    UserProfile = None
    DeviceFingerprint = None
    VelocityRecord = None
    AuditLog = None
    TransactionRepository = None
    AlertRepository = None
    CaseRepository = None
    UserRepository = None
    VelocityRepository = None

__all__ = [
    # Availability flags
    "SQLALCHEMY_AVAILABLE",
    "REDIS_AVAILABLE",
    "MODELS_AVAILABLE",
    # Session
    "get_db",
    "get_redis",
    "init_db",
    "close_db",
    "DatabaseSession",
    "RedisCache",
    "check_database_health",
    "check_redis_health",
    # Models
    "Base",
    "User",
    "APIKey",
    "Transaction",
    "FraudAlert",
    "Case",
    "CaseNote",
    "UserProfile",
    "DeviceFingerprint",
    "VelocityRecord",
    "AuditLog",
    # Repositories
    "TransactionRepository",
    "AlertRepository",
    "CaseRepository",
    "UserRepository",
    "VelocityRepository",
]
