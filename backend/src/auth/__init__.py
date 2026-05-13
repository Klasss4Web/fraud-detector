"""
Authentication and authorization for the fraud detection API.
Supports JWT tokens and API keys.

Note: Requires SQLAlchemy and database to be available.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Any
from uuid import UUID

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import BaseModel

# Optional imports
try:
    from jose import JWTError, jwt

    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTError = Exception
    jwt = None

try:
    from passlib.context import CryptContext

    PASSLIB_AVAILABLE = True
    pwd_context = CryptContext(
        schemes=["bcrypt"],
        deprecated="auto",
        bcrypt__truncate_error=False,  # Silently truncate passwords > 72 bytes instead of raising error
    )
except ImportError:
    PASSLIB_AVAILABLE = False
    pwd_context = None

try:
    from sqlalchemy.orm import Session
    from db.session import get_db, SQLALCHEMY_AVAILABLE
    from db.models import User, APIKey, UserRole
    from db.repository import UserRepository

    DB_AVAILABLE = SQLALCHEMY_AVAILABLE
except ImportError:
    DB_AVAILABLE = False
    Session = Any
    get_db = None
    User = None
    APIKey = None
    UserRole = None
    UserRepository = None

# ============== Configuration ==============

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ============== Models ==============


class TokenData(BaseModel):
    """JWT token payload data."""

    user_id: str
    email: str
    role: str
    scopes: List[str] = []


class Token(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreate(BaseModel):
    """User creation request."""

    email: str
    password: str
    full_name: str
    role: str = "viewer"  # Use string to avoid import issues


class UserResponse(BaseModel):
    """User response model."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


# ============== Password Utilities ==============


def _truncate_password(password: str) -> str:
    """Truncate password to 72 bytes (bcrypt limit)."""
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return encoded[:72].decode("utf-8", errors="ignore")
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    if not PASSLIB_AVAILABLE or pwd_context is None:
        raise RuntimeError("passlib not installed - cannot verify passwords")
    return pwd_context.verify(_truncate_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    if not PASSLIB_AVAILABLE or pwd_context is None:
        raise RuntimeError("passlib not installed - cannot hash passwords")
    return pwd_context.hash(_truncate_password(password))


# ============== JWT Token Utilities ==============


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    if not JWT_AVAILABLE or jwt is None:
        raise RuntimeError("python-jose not installed - cannot create tokens")
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    if not JWT_AVAILABLE or jwt is None:
        raise RuntimeError("python-jose not installed - cannot create tokens")
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    if not JWT_AVAILABLE or jwt is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        scopes = payload.get("scopes", [])

        if user_id is None:
            return None

        return TokenData(user_id=user_id, email=email, role=role, scopes=scopes)
    except JWTError:
        return None


# ============== API Key Utilities ==============


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash, key_prefix)
    """
    # Generate a secure random key
    full_key = f"fds_{secrets.token_urlsafe(32)}"
    key_prefix = full_key[:12]
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    return full_key, key_hash, key_prefix


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


# ============== Authentication Dependencies ==============


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract user from JWT token."""
    if not credentials:
        return None

    token_data = decode_token(credentials.credentials)
    if not token_data:
        return None

    repo = UserRepository(db)
    user = repo.get_by_id(UUID(token_data.user_id))

    if not user or not user.is_active:
        return None

    return user


async def get_current_user_from_api_key(
    api_key: str = Security(api_key_header), db: Session = Depends(get_db)
) -> Optional[Tuple[User, APIKey]]:
    """Extract user from API key."""
    if not api_key:
        return None

    key_hash = hash_api_key(api_key)
    repo = UserRepository(db)
    api_key_obj = repo.get_api_key_by_hash(key_hash)

    if not api_key_obj:
        return None

    user = repo.get_by_id(api_key_obj.user_id)
    if not user or not user.is_active:
        return None

    # Update last used timestamp
    repo.update_api_key_last_used(api_key_obj.id)

    return user, api_key_obj


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_result: Optional[Tuple[User, APIKey]] = Depends(get_current_user_from_api_key),
) -> User:
    """
    Get the current authenticated user from either JWT or API key.

    Raises HTTPException if not authenticated.
    """
    if token_user:
        return token_user

    if api_key_result:
        return api_key_result[0]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_result: Optional[Tuple[User, APIKey]] = Depends(get_current_user_from_api_key),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if token_user:
        return token_user
    if api_key_result:
        return api_key_result[0]
    return None


# ============== Authorization Dependencies ==============


def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory to require specific roles.

    Usage:
        @app.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_role([UserRole.ADMIN]))):
            ...
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized for this action",
            )
        return current_user

    return role_checker


def require_scope(required_scopes: List[str]):
    """
    Dependency factory to require specific API key scopes.

    Usage:
        @app.post("/analyze")
        def analyze(user: User = Depends(require_scope(["write:analyze"]))):
            ...
    """

    async def scope_checker(
        token_user: Optional[User] = Depends(get_current_user_from_token),
        api_key_result: Optional[Tuple[User, APIKey]] = Depends(get_current_user_from_api_key),
    ) -> User:
        # JWT tokens have full access based on role
        if token_user:
            return token_user

        # API keys need specific scopes
        if api_key_result:
            user, api_key = api_key_result

            for scope in required_scopes:
                if scope not in api_key.scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"API key missing required scope: {scope}",
                    )

            return user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return scope_checker


# ============== Auth Service ==============


class AuthService:
    """Authentication service for user management."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.user_repo.get_by_email(email)

        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        # Update last login
        self.user_repo.update_last_login(user.id)

        return user

    def create_user(
        self, email: str, password: str, full_name: str, role: UserRole = UserRole.VIEWER
    ) -> User:
        """Create a new user."""
        # Check if user exists
        if self.user_repo.get_by_email(email):
            raise ValueError("User with this email already exists")

        hashed_password = get_password_hash(password)
        return self.user_repo.create_user(
            email=email, hashed_password=hashed_password, full_name=full_name, role=role
        )

    def create_tokens(self, user: User) -> Token:
        """Create access and refresh tokens for a user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def refresh_tokens(self, refresh_token: str) -> Optional[Token]:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("sub")
            user = self.user_repo.get_by_id(UUID(user_id))

            if not user or not user.is_active:
                return None

            return self.create_tokens(user)

        except JWTError:
            return None

    def create_api_key(
        self, user_id: UUID, name: str, scopes: List[str], expires_in_days: int = None
    ) -> Tuple[str, APIKey]:
        """
        Create a new API key for a user.

        Returns:
            Tuple of (full_key, api_key_object)

        Note: The full_key is only returned once and should be shown to the user.
        """
        full_key, key_hash, key_prefix = generate_api_key()

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = self.user_repo.create_api_key(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            scopes=scopes,
            expires_at=expires_at,
        )

        return full_key, api_key


# ============== Role Hierarchy ==============

ROLE_HIERARCHY = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.SENIOR_ANALYST: 3,
    UserRole.ADMIN: 4,
    UserRole.API_CLIENT: 1,
}


def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """Check if user role has permission for required role level."""
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)


# ============== Scope Definitions ==============

AVAILABLE_SCOPES = {
    "read:transactions": "Read transaction data",
    "read:alerts": "Read fraud alerts",
    "read:cases": "Read investigation cases",
    "write:analyze": "Submit transactions for analysis",
    "write:alerts": "Update alert status",
    "write:cases": "Create and update cases",
    "admin:users": "Manage users",
    "admin:config": "Modify system configuration",
}

DEFAULT_SCOPES = ["read:transactions", "read:alerts", "write:analyze"]
