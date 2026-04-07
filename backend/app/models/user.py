from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True, default=None)
    bio: Mapped[str] = mapped_column(String(200), nullable=True, default=None)
    show_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_followers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_following: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    checkins = relationship("Checkin", back_populates="user", lazy="selectin")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
