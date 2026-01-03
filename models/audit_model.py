from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import SQLModel, Field


class AuditLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    action: str
    entity: str
    entity_id: Optional[UUID] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
