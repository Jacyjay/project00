from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    place_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("places.id"), nullable=True, index=True)
    location_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, default=None)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=True, default=None)
    visit_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False, default="photo")
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="checkins", lazy="selectin")
    place = relationship("Place", back_populates="checkins", lazy="selectin")
    photos = relationship("Photo", back_populates="checkin", lazy="selectin", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="checkin", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="checkin", cascade="all, delete-orphan")
