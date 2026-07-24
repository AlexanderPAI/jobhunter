import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.models.base import Base

if TYPE_CHECKING:
    from backend.db.models.job_search import CandidateProfile


class ResumeRecommendation(Base):
    __tablename__ = "resume_recommendations"
    __table_args__ = (
        Index(
            "ix_resume_recommendations_profile_created_at",
            "profile_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    skill: Mapped[str] = mapped_column(String(64), default="base")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    profile: Mapped["CandidateProfile"] = relationship(
        back_populates="resume_recommendations"
    )
