"""
Authentication API routes.
Requires: python-jose, passlib, sqlalchemy
"""

from typing import List, Optional

# Check dependencies before importing
try:
    from fastapi import APIRouter, Depends, HTTPException, status
    from pydantic import BaseModel, EmailStr, field_validator

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    raise ImportError("FastAPI is required for auth routes")

try:
    from sqlalchemy.orm import Session

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Session = None

from db.session import get_db
from db.models import User, UserRole

# Import auth module components (will fail gracefully if deps missing)
from auth import (
    AuthService,
    get_current_user,
    require_role,
    Token,
    UserResponse,
    AVAILABLE_SCOPES,
    DEFAULT_SCOPES,
    DB_AVAILABLE,
    JWT_AVAILABLE,
    PASSLIB_AVAILABLE,
)

# Check if all required dependencies are available
if not JWT_AVAILABLE:
    raise ImportError(
        "python-jose is required for auth routes. Install with: pip install python-jose[cryptography]"
    )

if not PASSLIB_AVAILABLE:
    raise ImportError(
        "passlib is required for auth routes. Install with: pip install passlib[bcrypt]"
    )

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============== Request/Response Models ==============


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes (bcrypt limitation)")
        return v


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_max_length(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes (bcrypt limitation)")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    """API key creation request."""

    name: str
    scopes: List[str] = DEFAULT_SCOPES
    expires_in_days: int = None


class APIKeyResponse(BaseModel):
    """API key response (includes full key only on creation)."""

    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    is_active: bool
    full_key: str = None  # Only returned on creation


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str


# ============== Auth Routes ==============


@router.post("/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.
    """
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_service.create_tokens(user)


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user (viewer role by default).

    Note: In production, this might require admin approval or be disabled.
    """
    auth_service = AuthService(db)

    try:
        user = auth_service.create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=UserRole.VIEWER,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    auth_service = AuthService(db)
    tokens = auth_service.refresh_tokens(request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    return tokens


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change current user's password.
    """
    from auth import verify_password, get_password_hash

    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


# ============== API Key Routes ==============


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for the current user.

    The full key is only returned once - make sure to save it!
    """
    # Validate scopes
    for scope in request.scopes:
        if scope not in AVAILABLE_SCOPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope: {scope}. Available: {list(AVAILABLE_SCOPES.keys())}",
            )

    auth_service = AuthService(db)
    full_key, api_key = auth_service.create_api_key(
        user_id=current_user.id,
        name=request.name,
        scopes=request.scopes,
        expires_in_days=request.expires_in_days,
    )

    return APIKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        full_key=full_key,  # Only returned on creation!
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """
    List all API keys for the current user.
    """
    return [
        APIKeyResponse(
            id=str(key.id),
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=key.scopes,
            is_active=key.is_active,
        )
        for key in current_user.api_keys
    ]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Revoke an API key.
    """
    from uuid import UUID
    from db.models import APIKey

    api_key = (
        db.query(APIKey)
        .filter(APIKey.id == UUID(key_id), APIKey.user_id == current_user.id)
        .first()
    )

    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    api_key.is_active = False
    db.commit()

    return {"message": "API key revoked"}


@router.get("/scopes")
async def list_available_scopes():
    """
    List all available API key scopes.
    """
    return AVAILABLE_SCOPES


# ============== Admin Routes ==============


@router.post("/users", response_model=UserResponse)
async def create_user_admin(
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    Create a new user (admin only).
    """
    auth_service = AuthService(db)

    try:
        user = auth_service.create_user(
            email=email, password=password, full_name=full_name, role=role
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_role([UserRole.ADMIN])), db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    """
    from db.models import User as UserModel

    users = db.query(UserModel).all()

    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        )
        for user in users
    ]
