from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    nickname: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserPublicOut(BaseModel):
    id: int
    nickname: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime
    # Conditionally populated: present when show_email=True or viewer is the owner
    email: Optional[str] = None
    show_email: bool = True
    show_followers: bool = True
    show_following: bool = True

    class Config:
        from_attributes = True


class CurrentUserOut(UserPublicOut):
    email: str  # always present for the owner themselves


class UserStats(BaseModel):
    total_checkins: int
    total_places: int
    total_photos: int


class ShowEmailUpdate(BaseModel):
    show_email: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: CurrentUserOut
