from app.db.base import Base
from app.db.session import engine

# Import all models so SQLAlchemy registers them before create_all
from app.models import user, transaction, audit_log  # noqa: F401


def init_db() -> None:
    """
    Creates all tables defined in models.
    In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
