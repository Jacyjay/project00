from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Journey(Base):
    __tablename__ = "journeys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", lazy="selectin")
    journey_checkins = relationship(
        "JourneyCheckin",
        back_populates="journey",
        order_by="JourneyCheckin.sort_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JourneyCheckin(Base):
    __tablename__ = "journey_checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    journey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("journeys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkin_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checkins.id", ondelete="CASCADE"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    journey = relationship("Journey", back_populates="journey_checkins")
    checkin = relationship("Checkin", lazy="selectin")
