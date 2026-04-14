from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class PlaceCreate(BaseModel):
    name: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    cover_image: Optional[str] = None
    description: Optional[str] = None


class PlaceOut(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    cover_image: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    checkin_count: int = 0
    user_count: int = 0
    photo_count: int = 0

    class Config:
        from_attributes = True


class PlaceMapItem(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    latitude: float
    longitude: float
    cover_image: Optional[str] = None
    checkin_count: int = 0
    user_count: int = 0

    class Config:
        from_attributes = True
