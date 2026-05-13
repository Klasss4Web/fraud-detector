"""
Fraud Detection API - Main Application Module
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .routes import router, init_orchestrator
from .observability_routes import router as observability_router
from .error_handlers import (
    ErrorHandlingMiddleware,
    APIError,
    api_error_handler,
    generic_exception_handler,
)
from src.observability import setup_logging as setup_structured_logging


def setup_logging(log_level: str) -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger = logging.getLogger("api")
    logger.info("Initializing Fraud Detection API...")

    # Initialize database (optional - gracefully handle if not available)
    try:
        from db.session import init_db, check_database_health, check_redis_health

        # Check database health
        db_health = check_database_health()
        if db_health["status"] == "healthy":
            logger.info("PostgreSQL database connected")
            init_db()
        else:
            logger.warning(f"PostgreSQL not available: {db_health.get('error', 'Unknown')}")
            logger.warning("Running in memory-only mode (data will not persist)")

        # Check Redis health
        redis_health = check_redis_health()
        if redis_health["status"] == "healthy":
            logger.info("Redis cache connected")
        else:
            logger.warning(f"Redis not available: {redis_health.get('error', 'Unknown')}")
            logger.warning("Running without cache (reduced performance)")
    except ImportError:
        logger.warning("Database module not available, running in memory-only mode")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.warning("Running in memory-only mode")

    # Start metrics persistence scheduler
    try:
        from observability import start_metrics_persistence, get_metrics_persistence

        persistence = get_metrics_persistence()
        if persistence.is_available:
            start_metrics_persistence()
            logger.info("Metrics persistence scheduler started")
        else:
            logger.info("Metrics persistence disabled (database not available)")
    except ImportError:
        logger.debug("Metrics persistence module not available")
    except Exception as e:
        logger.warning(f"Failed to start metrics persistence: {e}")

    # Initialize the orchestrator
    init_orchestrator(settings)
    logger.info("Orchestrator initialized successfully")

    if settings.enable_llm and settings.openai_api_key:
        logger.info("LLM investigation agent enabled")
    else:
        logger.info("LLM investigation agent disabled (no API key)")

    yield

    # Cleanup
    logger.info("Shutting down Fraud Detection API...")

    # Stop metrics persistence
    try:
        from observability import stop_metrics_persistence

        stop_metrics_persistence()
        logger.info("Metrics persistence scheduler stopped")
    except Exception:
        pass

    try:
        from db.session import close_db

        close_db()
    except Exception:
        pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="""
## Multi-Agent Fraud Detection System

A comprehensive fraud detection API that uses specialized AI agents to detect fraud across:

- **Financial Transactions**: Velocity attacks, amount anomalies, geographic risks
- **Insurance Claims**: Staged incidents, exaggerated claims, serial claimants
- **Identity Verification**: Synthetic identity, account takeover, identity theft
- **E-commerce Orders**: Reseller fraud, stolen cards, friendly fraud

### Features (v0.2.0)

- **PostgreSQL Persistence**: Transaction history, alerts, cases stored in database
- **Redis Caching**: Fast velocity checks and session management
- **JWT Authentication**: Secure API access with role-based permissions
- **API Key Support**: Programmatic access with scoped permissions
- **Real IP Intelligence**: Integration with IPinfo.io and IP-API
- **Impossible Travel Detection**: Detects physically impossible location changes
- **Dynamic Thresholds**: User-specific limits based on behavioral history
- **Webhook Integration**: Receive chargebacks and fraud confirmations

### Risk Levels

| Score Range | Level | Typical Action |
|-------------|-------|----------------|
| 80-100 | CRITICAL | Block/Deny immediately |
| 60-79 | HIGH | Require verification |
| 40-59 | MEDIUM | Enhanced monitoring |
| 0-39 | LOW | Standard processing |
        """,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Register exception handlers
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with consistent format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP_ERROR",
                "message": exc.detail,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with sanitized details."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"][1:])  # Skip 'body'
            errors.append(f"{field}: {error['msg']}")

        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
            },
        )

    # Include routes
    from .observability_plots import router as observability_plots_router

    # Main API routes
    app.include_router(router, prefix="/api/v1")
    app.include_router(observability_router, prefix="/api/v1")
    app.include_router(observability_plots_router, prefix="/api/v1")

    # Authentication routes (optional - requires db module)
    try:
        from auth.routes import router as auth_router

        app.include_router(auth_router, prefix="/api/v1")
        logging.getLogger("api").info("Authentication routes loaded")
    except ImportError as e:
        logging.getLogger("api").debug(f"Auth routes not available: {e}")
    except Exception as e:
        logging.getLogger("api").warning(f"Auth routes failed to load: {e}")

    # Webhook routes (optional - requires db module)
    try:
        from .webhooks import router as webhook_router

        app.include_router(webhook_router, prefix="/api/v1")
        logging.getLogger("api").info("Webhook routes loaded")
    except ImportError as e:
        logging.getLogger("api").debug(f"Webhook routes not available: {e}")
    except Exception as e:
        logging.getLogger("api").warning(f"Webhook routes failed to load: {e}")

    return app


# Create the app instance
app = create_app()


def main() -> None:
    """Run the API server."""
    settings = get_settings()
    uvicorn.run(
        "api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
