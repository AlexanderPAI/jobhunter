import uuid
from typing import Optional

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.models.base import Base


class Test(Base):
    __tablename__ = "test"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    description: Mapped[Optional[str]] = mapped_column(String(4096))
