"""
Tests for the authentication module.
"""

import pytest
from fastapi.testclient import TestClient
from db.models import User, UserRole


class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "viewer"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with existing email fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "testuser@example.com",  # Already exists
                "password": "anotherpassword123",
                "full_name": "Another User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
                "full_name": "Invalid Email User",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client):
        """Test registration with too short password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpass@example.com",
                "password": "short",  # Less than 8 characters
                "full_name": "Short Password User",
            },
        )

        assert response.status_code == 422
        assert "at least 8 characters" in response.text.lower()

    def test_register_missing_fields(self, client):
        """Test registration with missing required fields."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "incomplete@example.com"},
        )

        assert response.status_code == 422


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "somepassword"},
        )

        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user."""
        from auth import get_password_hash

        # Create inactive user
        user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("password123"),
            full_name="Inactive User",
            role=UserRole.VIEWER,
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "password123"},
        )

        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(self, client, test_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "testpassword123"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Now refresh
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401


class TestCurrentUser:
    """Tests for getting current user info."""

    def test_get_current_user_success(self, client, auth_headers):
        """Test getting current user info with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["full_name"] == "Test User"

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code in [401, 403]

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code in [401, 403]


class TestChangePassword:
    """Tests for password change endpoint."""

    def test_change_password_success(self, client, test_user, auth_headers):
        """Test successful password change."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 200

        # Verify can login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "testuser@example.com", "password": "newpassword456"},
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, client, auth_headers):
        """Test password change with wrong current password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code in [400, 401]

    def test_change_password_short_new(self, client, auth_headers):
        """Test password change with too short new password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "short",
            },
        )

        assert response.status_code == 422


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_admin_can_list_users(self, client, admin_auth_headers):
        """Test that admin can list all users."""
        response = client.get("/api/v1/auth/users", headers=admin_auth_headers)

        # Admin should have access
        assert response.status_code == 200

    def test_viewer_cannot_list_users(self, client, auth_headers):
        """Test that viewer cannot list all users."""
        response = client.get("/api/v1/auth/users", headers=auth_headers)

        # Viewer should be denied
        assert response.status_code == 403

    def test_admin_can_create_user(self, client, admin_auth_headers):
        """Test that admin can create users."""
        response = client.post(
            "/api/v1/auth/users",
            headers=admin_auth_headers,
            json={
                "email": "createdbyAdmin@example.com",
                "password": "password123",
                "full_name": "Created By Admin",
                "role": "analyst",
            },
        )

        assert response.status_code == 200
        assert response.json()["role"] == "analyst"


class TestAPIKeys:
    """Tests for API key management."""

    def test_create_api_key(self, client, auth_headers):
        """Test creating an API key."""
        response = client.post(
            "/api/v1/auth/api-keys",
            headers=auth_headers,
            json={
                "name": "Test API Key",
                "scopes": ["read:transactions"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "key" in data  # Full key returned on creation
        assert data["name"] == "Test API Key"

    def test_list_api_keys(self, client, auth_headers):
        """Test listing user's API keys."""
        # Create a key first
        client.post(
            "/api/v1/auth/api-keys",
            headers=auth_headers,
            json={"name": "Key for listing", "scopes": ["read:transactions"]},
        )

        response = client.get("/api/v1/auth/api-keys", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_delete_api_key(self, client, auth_headers):
        """Test deleting an API key."""
        # Create a key first
        create_response = client.post(
            "/api/v1/auth/api-keys",
            headers=auth_headers,
            json={"name": "Key to delete", "scopes": ["read:transactions"]},
        )
        key_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=auth_headers)

        assert response.status_code == 200

    def test_get_available_scopes(self, client, auth_headers):
        """Test getting available API scopes."""
        response = client.get("/api/v1/auth/scopes", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "scopes" in data
