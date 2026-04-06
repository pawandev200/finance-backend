from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

# ── Engine Setup ─────────────────────────────────────────────────────────────
# connect_args is SQLite-specific — remove for PostgreSQL
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # Pool settings (relevant for PostgreSQL in production)
    pool_pre_ping=True,       # Checks connections before use
    echo=settings.DEBUG,      # Log SQL queries in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── FastAPI Dependency ────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    Yields a database session and ensures it's closed after use.
    Used as a FastAPI dependency via Depends(get_db).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
