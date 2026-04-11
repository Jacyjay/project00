from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user, get_optional_user
from app.models.user import User
from app.crud import journey as journey_crud

router = APIRouter(prefix="/api/journeys", tags=["journeys"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CreateJourneyRequest(BaseModel):
    title: str
    checkin_ids: list[int]
    is_public: bool = True


# ── Serializers ────────────────────────────────────────────────────────────────

def _serialize_checkin(jc) -> dict:
    c = jc.checkin
    photo_url = c.photos[0].image_url if c.photos else None
    return {
        "id": c.id,
        "location_name": c.location_name,
        "city": c.city,
        "address": c.address,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "content": c.content,
        "visit_date": str(c.visit_date) if c.visit_date else None,
        "created_at": c.created_at.isoformat(),
        "preview_image_url": photo_url,
        "sort_order": jc.sort_order,
    }


def _serialize_journey(journey, detailed: bool = False) -> dict:
    checkins = [_serialize_checkin(jc) for jc in journey.journey_checkins]
    # Deduplicated city list in order of appearance
    seen: set[str] = set()
    cities: list[str] = []
    for c in checkins:
        city = c.get("city") or ""
        if city and city not in seen:
            seen.add(city)
            cities.append(city)

    dates = [c["visit_date"] or c["created_at"][:10] for c in checkins if c["visit_date"] or c["created_at"]]

    data: dict = {
        "id": journey.id,
        "title": journey.title,
        "is_public": journey.is_public,
        "created_at": journey.created_at.isoformat(),
        "checkin_count": len(checkins),
        "cities": cities,
        "start_date": min(dates) if dates else None,
        "end_date": max(dates) if dates else None,
        "user": {
            "id": journey.user_id,
            "nickname": journey.user.nickname,
            "avatar_url": journey.user.avatar_url,
        },
    }
    if detailed:
        data["checkins"] = checkins
    return data


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("", summary="创建旅程")
async def create_journey(
    body: CreateJourneyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not body.checkin_ids:
        raise HTTPException(status_code=400, detail="至少需要一个打卡点")
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="旅程标题不能为空")
    journey = await journey_crud.create_journey(
        db, current_user.id, body.title.strip(), body.checkin_ids, body.is_public
    )
    return _serialize_journey(journey, detailed=False)


@router.get("/me", summary="我的旅程列表")
async def my_journeys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journeys = await journey_crud.list_user_journeys(db, current_user.id)
    return [_serialize_journey(j) for j in journeys]


@router.get("/{journey_id}", summary="旅程详情（公开可访问）")
async def get_journey(
    journey_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    journey = await journey_crud.get_journey(db, journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="旅程不存在")
    if not journey.is_public and (not current_user or current_user.id != journey.user_id):
        raise HTTPException(status_code=403, detail="此旅程未公开")
    return _serialize_journey(journey, detailed=True)


@router.delete("/{journey_id}", summary="删除旅程")
async def delete_journey(
    journey_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await journey_crud.delete_journey(db, journey_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="旅程不存在或无权删除")
    return {"status": "deleted"}
