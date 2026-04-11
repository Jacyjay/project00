from __future__ import annotations

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.journey import Journey, JourneyCheckin
from app.models.checkin import Checkin


async def create_journey(
    db: AsyncSession,
    user_id: int,
    title: str,
    checkin_ids: list[int],
    is_public: bool = True,
) -> Journey:
    journey = Journey(user_id=user_id, title=title, is_public=is_public)
    db.add(journey)
    await db.flush()

    for order, cid in enumerate(checkin_ids):
        db.add(JourneyCheckin(journey_id=journey.id, checkin_id=cid, sort_order=order))

    await db.commit()
    # Reload with full relationships
    return await get_journey(db, journey.id)


async def get_journey(db: AsyncSession, journey_id: int) -> Optional[Journey]:
    result = await db.execute(
        select(Journey)
        .where(Journey.id == journey_id)
        .options(
            selectinload(Journey.journey_checkins)
            .selectinload(JourneyCheckin.checkin)
            .selectinload(Checkin.photos)
        )
    )
    return result.scalar_one_or_none()


async def list_user_journeys(db: AsyncSession, user_id: int) -> List[Journey]:
    result = await db.execute(
        select(Journey)
        .where(Journey.user_id == user_id)
        .order_by(Journey.created_at.desc())
        .options(
            selectinload(Journey.journey_checkins)
            .selectinload(JourneyCheckin.checkin)
            .selectinload(Checkin.photos)
        )
    )
    return list(result.scalars().all())


async def delete_journey(db: AsyncSession, journey_id: int, user_id: int) -> bool:
    journey = await db.get(Journey, journey_id)
    if not journey or journey.user_id != user_id:
        return False
    await db.delete(journey)
    await db.commit()
    return True
