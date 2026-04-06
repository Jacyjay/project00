from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, get_current_user
from app.crud.message import (
    send_message, get_conversation, get_conversations,
    mark_messages_read, get_unread_count
)
from app.crud.user import get_user_by_id
from app.schemas.message import MessageOut, MessageCreate, ConversationOut
from app.models.user import User
from app.models.message import Message

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _msg_to_out(msg: Message) -> MessageOut:
    return MessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        receiver_id=msg.receiver_id,
        content=msg.content,
        is_read=msg.is_read,
        created_at=_ensure_utc(msg.created_at),
        sender_nickname=msg.sender.nickname if msg.sender else "",
        sender_avatar=msg.sender.avatar_url if msg.sender else None,
        receiver_nickname=msg.receiver.nickname if msg.receiver else "",
        receiver_avatar=msg.receiver.avatar_url if msg.receiver else None,
    )


@router.get("/unread-count")
async def get_my_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = await get_unread_count(db, current_user.id)
    return {"count": count}


@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    messages = await get_conversations(db, current_user.id)
    result = []
    for msg in messages:
        is_sender = msg.sender_id == current_user.id
        partner = msg.receiver if is_sender else msg.sender
        if not partner:
            continue
        unread_res = await db.execute(
            select(func.count(Message.id)).where(
                and_(
                    Message.sender_id == partner.id,
                    Message.receiver_id == current_user.id,
                    Message.is_read == False,
                )
            )
        )
        unread = unread_res.scalar_one() or 0
        result.append(ConversationOut(
            partner_id=partner.id,
            partner_nickname=partner.nickname,
            partner_avatar=partner.avatar_url,
            last_message=msg.content[:60] + ("…" if len(msg.content) > 60 else ""),
            last_message_time=_ensure_utc(msg.created_at),
            unread_count=unread,
        ))
    return result


@router.get("/{partner_id}", response_model=List[MessageOut])
async def get_messages_with_user(
    partner_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    partner = await get_user_by_id(db, partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="用户不存在")

    await mark_messages_read(db, current_user.id, partner_id)
    msgs = await get_conversation(db, current_user.id, partner_id, limit, offset)
    return [_msg_to_out(m) for m in msgs]


@router.post("/{partner_id}", response_model=MessageOut)
async def send_message_to_user(
    partner_id: int,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if partner_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己发送私信")

    partner = await get_user_by_id(db, partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="用户不存在")

    msg = await send_message(db, current_user.id, partner_id, data.content.strip())
    return _msg_to_out(msg)
