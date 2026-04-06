"""
AuditLog — Every state-changing action in the system is recorded here.
This is non-negotiable in financial systems for compliance and debugging.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # What happened
    action = Column(String(50), nullable=False)       # CREATE | UPDATE | DELETE | LOGIN | LOGOUT
    resource = Column(String(50), nullable=False)     # transaction | user
    resource_id = Column(String(36), nullable=True)

    # State snapshots for diff/rollback visibility
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)    # IPv6 max length = 45
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog user={self.user_id} action={self.action} resource={self.resource}>"
