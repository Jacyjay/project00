from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, and_, func, update, case
from sqlalchemy.orm import selectinload
from app.models.message import Message

MESSAGE_LOAD_OPTIONS = (
    selectinload(Message.sender),
    selectinload(Message.receiver),
)


async def send_message(db: AsyncSession, sender_id: int, receiver_id: int, content: str) -> Message:
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    # Re-fetch with eager-loaded relationships
    result = await db.execute(
        select(Message).options(*MESSAGE_LOAD_OPTIONS).where(Message.id == msg.id)
    )
    return result.scalar_one()


async def get_conversation(
    db: AsyncSession, user_id: int, partner_id: int,
    limit: int = 50, offset: int = 0
) -> List[Message]:
    result = await db.execute(
        select(Message)
        .options(*MESSAGE_LOAD_OPTIONS)
        .where(
            or_(
                and_(Message.sender_id == user_id, Message.receiver_id == partner_id),
                and_(Message.sender_id == partner_id, Message.receiver_id == user_id),
            )
        )
        .order_by(desc(Message.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(reversed(result.scalars().all()))


async def mark_messages_read(db: AsyncSession, reader_id: int, sender_id: int) -> None:
    await db.execute(
        update(Message)
        .where(
            Message.receiver_id == reader_id,
            Message.sender_id == sender_id,
            Message.is_read == False,
        )
        .values(is_read=True)
    )
    await db.commit()


async def get_conversations(db: AsyncSession, user_id: int) -> List[Message]:
    """Return the most recent message for each unique conversation partner."""
    partner_expr = case(
        (Message.sender_id == user_id, Message.receiver_id),
        else_=Message.sender_id,
    )
    subq = (
        select(func.max(Message.id))
        .where(or_(Message.sender_id == user_id, Message.receiver_id == user_id))
        .group_by(partner_expr)
        .scalar_subquery()
    )
    result = await db.execute(
        select(Message)
        .options(*MESSAGE_LOAD_OPTIONS)
        .where(Message.id.in_(subq))
        .order_by(desc(Message.created_at))
    )
    return result.scalars().all()


async def get_unread_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Message.id)).where(
            Message.receiver_id == user_id,
            Message.is_read == False,
        )
    )
    return result.scalar_one() or 0
