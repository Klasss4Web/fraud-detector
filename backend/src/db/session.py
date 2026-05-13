"""
Database session management for PostgreSQL and Redis.
Both are OPTIONAL - system works without them using in-memory fallbacks.
"""

import os
from typing import Generator, Optional, Any
from contextlib import contextmanager
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(override=True)  # Load environment variables from .env file

# ============== Optional Imports ==============

# SQLAlchemy (optional)
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import QueuePool

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = Any  # Type hint fallback
    logger.info("SQLAlchemy not installed - database features disabled")

# Redis (optional)
try:
    import redis as redis_lib

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis_lib = None
    logger.info("Redis not installed - using in-memory cache")


# ============== Configuration ==============


def get_database_url() -> str:
    """Get PostgreSQL connection URL from environment."""
    environment = os.getenv("ENVIRONMENT")
    print(f"Database URL from environment inside function: @@@@@ {environment}")
    return os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fraud_detection"
    )


def get_redis_url() -> str:
    """Get Redis connection URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


# ============== PostgreSQL Engine & Session ==============

_engine = None
_SessionLocal = None
_Base = None


def _get_base():
    """Lazy load Base to avoid import errors when SQLAlchemy not available."""
    global _Base
    if _Base is None and SQLALCHEMY_AVAILABLE:
        from .models import Base

        _Base = Base
    return _Base


def _ensure_database_exists(database_url: str) -> bool:
    """
    Ensure the target database exists, creating it if necessary.
    Returns True if database exists or was created, False on failure.
    """
    from urllib.parse import urlparse

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/")

    # Build URL to connect to 'postgres' default database
    server_url = f"{parsed.scheme}://{parsed.netloc}/postgres"

    try:
        # Connect to default postgres database
        temp_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with temp_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": db_name}
            )
            exists = result.fetchone() is not None

            if not exists:
                logger.info(f"Database '{db_name}' does not exist, creating...")
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info(f"Database '{db_name}' created successfully")

        temp_engine.dispose()
        return True
    except Exception as e:
        logger.debug(f"Could not ensure database exists: {e}")
        return False


def get_engine():
    """Get or create SQLAlchemy engine. Returns None if not available."""
    global _engine

    if not SQLALCHEMY_AVAILABLE:
        return None

    if _engine is None:
        database_url = get_database_url()

        # Ensure database exists before connecting
        _ensure_database_exists(database_url)

        try:
            _engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            )
            logger.info(f"Database engine created for {database_url.split('@')[-1]}")
        except Exception as e:
            logger.debug(f"Failed to create database engine: {e}")
            return None
    return _engine


def get_session_factory():
    """Get or create session factory. Returns None if not available."""
    global _SessionLocal

    if not SQLALCHEMY_AVAILABLE:
        return None

    engine = get_engine()
    if engine is None:
        return None

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def get_db() -> Generator[Optional[Any], None, None]:
    """
    Dependency for FastAPI to get a database session.
    Yields None if database is not available.
    """
    SessionLocal = get_session_factory()
    if SessionLocal is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def DatabaseSession() -> Generator[Optional[Any], None, None]:
    """
    Context manager for database sessions.
    Yields None if database is not available.
    """
    SessionLocal = get_session_factory()
    if SessionLocal is None:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============== Redis Connection ==============

_redis_client = None


def get_redis():
    """
    Get Redis client for caching.
    Returns None if Redis is not available or disabled.
    """
    global _redis_client

    if not REDIS_AVAILABLE:
        return None

    # Allow disabling Redis via environment
    if os.getenv("REDIS_ENABLED", "true").lower() == "false":
        return None

    if _redis_client is None:
        try:
            redis_url = get_redis_url()
            _redis_client = redis_lib.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis connected: {redis_url.split('@')[-1]}")
        except Exception as e:
            logger.debug(f"Redis not available: {e}")
            _redis_client = None

    return _redis_client


class RedisCache:
    """
    Redis cache wrapper with in-memory fallback.
    Works perfectly fine without Redis.
    """

    def __init__(self):
        self._client = get_redis()
        self._local_cache = {}  # In-memory fallback
        self._local_expiry = {}  # Track expiry for local cache

    @property
    def available(self) -> bool:
        return self._client is not None

    def _cleanup_expired(self, key: str):
        """Remove expired local cache entries."""
        import time

        if key in self._local_expiry:
            if time.time() > self._local_expiry[key]:
                self._local_cache.pop(key, None)
                self._local_expiry.pop(key, None)

    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if self._client:
            try:
                return self._client.get(key)
            except Exception:
                pass

        self._cleanup_expired(key)
        return self._local_cache.get(key)

    def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in cache with TTL (default 5 minutes)."""
        import time

        if self._client:
            try:
                return self._client.setex(key, ttl, value)
            except Exception:
                pass

        self._local_cache[key] = value
        self._local_expiry[key] = time.time() + ttl
        return True

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self._client:
            try:
                return self._client.delete(key) > 0
            except Exception:
                pass

        deleted = key in self._local_cache
        self._local_cache.pop(key, None)
        self._local_expiry.pop(key, None)
        return deleted

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        if self._client:
            try:
                return self._client.incr(key, amount)
            except Exception:
                pass

        current = int(self._local_cache.get(key, 0))
        self._local_cache[key] = str(current + amount)
        return current + amount

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key."""
        import time

        if self._client:
            try:
                return self._client.expire(key, ttl)
            except Exception:
                pass

        if key in self._local_cache:
            self._local_expiry[key] = time.time() + ttl
            return True
        return False

    def get_velocity(self, entity_type: str, entity_id: str, window: str) -> dict:
        """Get velocity data for an entity."""
        import json

        key = f"velocity:{entity_type}:{entity_id}:{window}"
        data = self.get(key)
        if data:
            try:
                return json.loads(data)
            except Exception:
                pass
        return {"count": 0, "total_amount": 0.0, "unique_merchants": 0}

    def update_velocity(
        self,
        entity_type: str,
        entity_id: str,
        window: str,
        amount: float,
        merchant: str = None,
        ttl_seconds: int = None,
    ) -> dict:
        """Update velocity counters for an entity."""
        import json

        key = f"velocity:{entity_type}:{entity_id}:{window}"
        default_ttls = {"1h": 3600, "6h": 21600, "24h": 86400, "7d": 604800}
        ttl = ttl_seconds or default_ttls.get(window, 86400)

        # Get current and update
        data = self.get_velocity(entity_type, entity_id, window)
        data["count"] = data.get("count", 0) + 1
        data["total_amount"] = data.get("total_amount", 0.0) + amount
        if merchant:
            data["unique_merchants"] = data.get("unique_merchants", 0) + 1

        self.set(key, json.dumps(data), ttl)
        return data


# ============== Database Initialization ==============


def init_db(drop_all: bool = False):
    """
    Initialize database tables.
    Does nothing if database is not available.
    """
    if not SQLALCHEMY_AVAILABLE:
        logger.info("SQLAlchemy not available, skipping database init")
        return

    engine = get_engine()
    if engine is None:
        logger.info("No database connection, skipping init")
        return

    Base = _get_base()
    if Base is None:
        return

    if drop_all:
        logger.warning("Dropping all database tables!")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")


def close_db():
    """Close database connections."""
    global _engine, _SessionLocal, _redis_client

    if _engine:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("Database engine disposed")

    if _redis_client:
        try:
            _redis_client.close()
        except Exception:
            pass
        _redis_client = None


# ============== Health Checks ==============


def check_database_health() -> dict:
    """Check PostgreSQL connection health."""
    if not SQLALCHEMY_AVAILABLE:
        return {
            "status": "unavailable",
            "database": "postgresql",
            "reason": "SQLAlchemy not installed",
        }

    try:
        with DatabaseSession() as db:
            if db is None:
                return {
                    "status": "unavailable",
                    "database": "postgresql",
                    "reason": "No connection",
                }
            db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "postgresql"}
    except Exception as e:
        return {"status": "unhealthy", "database": "postgresql", "error": str(e)}


def check_redis_health() -> dict:
    """Check Redis connection health."""
    if not REDIS_AVAILABLE:
        return {"status": "unavailable", "cache": "redis", "reason": "Redis package not installed"}

    client = get_redis()
    if client is None:
        return {"status": "unavailable", "cache": "redis", "reason": "Not configured or disabled"}

    try:
        client.ping()
        return {"status": "healthy", "cache": "redis"}
    except Exception as e:
        return {"status": "unhealthy", "cache": "redis", "error": str(e)}
