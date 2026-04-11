from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AchievementBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    icon: str
    category: str
    rarity: str


class AchievementOut(AchievementBase):
    id: int
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserAchievementOut(BaseModel):
    achievement_code: str
    unlocked_at: datetime
    is_visible: bool

    class Config:
        from_attributes = True


class AchievementWithStatus(AchievementOut):
    """成就及其解锁状态"""
    unlocked: bool
    unlocked_at: Optional[datetime] = None
    is_visible: Optional[bool] = None
    progress: Optional[dict] = None  # {"current": 3, "target": 5}


class UpdateVisibilityRequest(BaseModel):
    is_visible: bool
