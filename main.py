"""
Finance Dashboard API — main.py
────────────────────────────────
Application entry point. Configures:
  - FastAPI app with metadata
  - CORS middleware
  - Request ID middleware
  - Rate limiting
  - Global exception handlers
  - API routers (versioned under /api/v1)
  - Database table creation on startup
  - Health check endpoint
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import init_db
from app.middleware.request_id import RequestIDMiddleware


# ── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown."""
    # Startup
    init_db()
    print(f" Database initialized")
    print(f" {settings.APP_NAME} v{settings.APP_VERSION} is running")
    yield
    # Shutdown (add cleanup here if needed)
    print(" Shutting down...")


# ── App Instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## Finance Dashboard API

A role-based financial records management system.

### Roles & Permissions
| Role    | Transactions | Dashboard Summary | Analytics & Trends | User Management |
|---------|:---:|:---:|:---:|:---:|
| Viewer  | Read only     | Yes              | No                | No              |
| Analyst | Read only     | Yes              | Yes               | No              |
| Admin   | Full access   | Yes              | Yes               | Yes             |

### Quick Start
1. Register or use seeded users (see README)
2. `POST /api/v1/auth/login` to get your token
3. Use `Bearer <token>` in the Authorization header
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── State for Rate Limiter ────────────────────────────────────────────────────
app.state.limiter = limiter

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception Handlers ────────────────────────────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Custom validation error handler — returns clean, structured errors
    instead of FastAPI's default verbose format.
    """
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed.", "errors": errors},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches unhandled exceptions and returns a safe 500 response."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"], summary="Health Check")
def health_check():
    """
    Used by load balancers and Docker health checks to verify the service is alive.
    Returns service name, version, and current uptime.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/", include_in_schema=False)
def root():
    return {"message": f"Welcome to {settings.APP_NAME}. Visit /docs for the API reference."}
