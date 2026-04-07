from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.crud.place import get_all_places, get_place_by_id, create_place, search_places
from app.schemas.place import PlaceCreate, PlaceOut, PlaceMapItem
from app.models.user import User
from app.services.region_normalizer import normalize_city_name

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("", response_model=List[PlaceMapItem])
async def list_places(
    q: Optional[str] = Query(None, description="搜索地点名称"),
    db: AsyncSession = Depends(get_db),
):
    if q:
        places = await search_places(db, q)
        return [PlaceMapItem(
            id=p.id, name=p.name, city=normalize_city_name(p.city),
            latitude=p.latitude, longitude=p.longitude,
            cover_image=p.cover_image, checkin_count=0, user_count=0,
        ) for p in places]
    places = await get_all_places(db)
    return [PlaceMapItem(**{**p, "city": normalize_city_name(p.get("city"))}) for p in places]


@router.get("/{place_id}", response_model=PlaceOut)
async def get_place(place_id: int, db: AsyncSession = Depends(get_db)):
    place = await get_place_by_id(db, place_id)
    if not place:
        raise HTTPException(status_code=404, detail="地点不存在")
    return PlaceOut(**{**place, "city": normalize_city_name(place.get("city"))})


@router.post("", response_model=PlaceOut)
async def add_place(
    data: PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    place = await create_place(db, **data.model_dump())
    place_data = await get_place_by_id(db, place.id)
    return PlaceOut(**{**place_data, "city": normalize_city_name(place_data.get("city"))})
