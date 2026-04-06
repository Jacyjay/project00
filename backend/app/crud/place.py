from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.place import Place
from app.models.checkin import Checkin
from app.models.photo import Photo


async def get_all_places(db: AsyncSession) -> List[dict]:
    """Get all places with checkin counts for map display."""
    result = await db.execute(select(Place))
    places = result.scalars().all()

    place_list = []
    for place in places:
        # Count checkins and unique users
        checkin_result = await db.execute(
            select(func.count(Checkin.id)).where(Checkin.place_id == place.id, Checkin.is_public == True)
        )
        checkin_count = checkin_result.scalar() or 0

        user_result = await db.execute(
            select(func.count(func.distinct(Checkin.user_id))).where(
                Checkin.place_id == place.id, Checkin.is_public == True
            )
        )
        user_count = user_result.scalar() or 0

        place_list.append({
            "id": place.id,
            "name": place.name,
            "city": place.city,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "cover_image": place.cover_image,
            "description": place.description,
            "created_at": place.created_at,
            "checkin_count": checkin_count,
            "user_count": user_count,
        })

    return place_list


async def get_place_by_id(db: AsyncSession, place_id: int) -> Optional[dict]:
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        return None

    checkin_result = await db.execute(
        select(func.count(Checkin.id)).where(Checkin.place_id == place.id, Checkin.is_public == True)
    )
    checkin_count = checkin_result.scalar() or 0

    user_result = await db.execute(
        select(func.count(func.distinct(Checkin.user_id))).where(
            Checkin.place_id == place.id, Checkin.is_public == True
        )
    )
    user_count = user_result.scalar() or 0

    photo_result = await db.execute(
        select(func.count(Photo.id)).join(Checkin).where(
            Checkin.place_id == place.id, Checkin.is_public == True
        )
    )
    photo_count = photo_result.scalar() or 0

    return {
        "id": place.id,
        "name": place.name,
        "city": place.city,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "cover_image": place.cover_image,
        "description": place.description,
        "created_at": place.created_at,
        "checkin_count": checkin_count,
        "user_count": user_count,
        "photo_count": photo_count,
    }


async def create_place(db: AsyncSession, **kwargs) -> Place:
    place = Place(**kwargs)
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place


async def search_places(db: AsyncSession, query: str) -> List[Place]:
    result = await db.execute(
        select(Place).where(Place.name.ilike(f"%{query}%"))
    )
    return result.scalars().all()
