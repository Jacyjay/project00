from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.models.checkin import Checkin
from app.models.photo import Photo


CHECKIN_LOAD_OPTIONS = (
    selectinload(Checkin.photos),
    selectinload(Checkin.user),
    selectinload(Checkin.place),
)


async def create_checkin(db: AsyncSession, user_id: int, location_name: str,
                         latitude: float, longitude: float,
                         city: str = None, address: str = None,
                         place_id: int = None, content: str = None, visit_date=None,
                         is_public: bool = True, media_type: str = "photo") -> Checkin:
    checkin = Checkin(
        user_id=user_id,
        place_id=place_id,
        location_name=location_name,
        city=city,
        address=address,
        latitude=latitude,
        longitude=longitude,
        content=content,
        visit_date=visit_date,
        is_public=is_public,
        media_type=media_type,
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)
    return checkin


async def add_photo_to_checkin(db: AsyncSession, checkin_id: int,
                                image_url: str, sort_order: int = 0) -> Photo:
    photo = Photo(
        checkin_id=checkin_id,
        image_url=image_url,
        sort_order=sort_order,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def get_checkins_by_place(db: AsyncSession, place_id: int,
                                 limit: int = 50, offset: int = 0) -> List[Checkin]:
    result = await db.execute(
        select(Checkin)
        .options(*CHECKIN_LOAD_OPTIONS)
        .where(Checkin.place_id == place_id, Checkin.is_public == True)
        .order_by(desc(Checkin.created_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_checkins_by_user(db: AsyncSession, user_id: int,
                                include_private: bool = False,
                                limit: int = 50, offset: int = 0) -> List[Checkin]:
    query = (
        select(Checkin)
        .options(*CHECKIN_LOAD_OPTIONS)
        .where(Checkin.user_id == user_id)
    )
    if not include_private:
        query = query.where(Checkin.is_public == True)
    query = query.order_by(desc(Checkin.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


async def get_photos_by_place(db: AsyncSession, place_id: int, limit: int = 50) -> List[Photo]:
    result = await db.execute(
        select(Photo)
        .join(Checkin)
        .where(Checkin.place_id == place_id, Checkin.is_public == True)
        .order_by(desc(Photo.created_at))
        .limit(limit)
    )
    return result.scalars().all()


async def get_public_map_checkins(db: AsyncSession, limit: int = 200) -> List[Checkin]:
    result = await db.execute(
        select(Checkin)
        .options(*CHECKIN_LOAD_OPTIONS)
        .where(Checkin.is_public == True)
        .order_by(desc(Checkin.created_at))
        .limit(limit)
    )
    return result.scalars().all()


async def get_checkin_by_id(db: AsyncSession, checkin_id: int) -> Optional[Checkin]:
    result = await db.execute(
        select(Checkin)
        .execution_options(populate_existing=True)
        .options(*CHECKIN_LOAD_OPTIONS)
        .where(Checkin.id == checkin_id)
    )
    return result.scalar_one_or_none()
