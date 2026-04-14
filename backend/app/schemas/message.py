from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    is_read: bool
    created_at: datetime
    sender_nickname: str = ""
    sender_avatar: Optional[str] = None
    receiver_nickname: str = ""
    receiver_avatar: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    partner_id: int
    partner_nickname: str
    partner_avatar: Optional[str] = None
    last_message: str
    last_message_time: datetime
    unread_count: int
