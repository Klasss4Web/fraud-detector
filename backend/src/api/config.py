"""
Application configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    app_name: str = "Fraud Detection API"
    app_version: str = "0.2.0"
    debug: bool = False

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS Settings
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database Settings
    database_url: str = None
    redis_url: str = "redis://localhost:6379/0"
    sql_echo: bool = False  # Log SQL queries

    # Authentication Settings
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # OpenAI/LLM Settings (for investigation agent)
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    enable_llm: bool = True

    # External Service API Keys
    ipinfo_token: Optional[str] = None
    maxmind_license_key: Optional[str] = None
    abstract_api_key: Optional[str] = None  # For email validation

    # Fraud Detection Settings
    auto_investigate_threshold: float = 60.0
    high_risk_threshold: float = 60.0

    # ML Model Settings
    enable_ml: bool = True
    ml_model_name: Optional[str] = None  # None = use default model
    ml_rule_weight: float = 0.6  # Weight for rule-based scoring (0-1)
    ml_model_weight: float = 0.4  # Weight for ML model scoring (0-1)
    ml_retraining_threshold: int = 1000  # Number of labeled samples before retraining

    # Webhook Settings
    webhook_secret: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
