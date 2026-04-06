from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


class PhotoOut(BaseModel):
    id: int
    image_url: str
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class CheckinCreate(BaseModel):
    location_name: str
    latitude: float
    longitude: float
    city: Optional[str] = None
    address: Optional[str] = None
    content: Optional[str] = None
    visit_date: Optional[date] = None
    is_public: bool = True


class CheckinOut(BaseModel):
    id: int
    user_id: int
    place_id: Optional[int] = None
    location_name: str
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float
    content: Optional[str] = None
    visit_date: Optional[date] = None
    is_public: bool
    created_at: datetime
    photos: List[PhotoOut] = Field(default_factory=list)
    user_nickname: str = ""
    user_avatar: Optional[str] = None
    place_name: str = ""
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    media_type: str = "photo"
    video_url: Optional[str] = None

    class Config:
        from_attributes = True


class CheckinMapItem(BaseModel):
    id: int
    user_id: int
    user_nickname: str = ""
    user_avatar: Optional[str] = None
    location_name: str
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float
    preview_text: Optional[str] = None
    preview_image_url: Optional[str] = None
    photo_count: int = 0
    visit_date: Optional[date] = None
    created_at: datetime
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    media_type: str = "photo"
    video_url: Optional[str] = None


class ReverseGeocodeOut(BaseModel):
    city: Optional[str] = None
    address: Optional[str] = None


class PlaceSearchOut(BaseModel):
    id: str
    name: str
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: float
    longitude: float
