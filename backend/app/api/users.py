from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from app.core.deps import get_db, get_current_user, get_optional_user
from app.core.config import settings
from app.crud.user import get_user_by_id
from app.schemas.user import UserPublicOut, UserStats, ShowEmailUpdate
from app.models.checkin import Checkin
from app.models.photo import Photo
from app.models.user import User
from app.services.image_upload import prepare_uploaded_image

router = APIRouter(prefix="/api/users", tags=["users"])


def _build_public_out(user: User, viewer: Optional[User] = None) -> UserPublicOut:
    """Serialize a User to UserPublicOut, exposing email based on visibility rules."""
    is_owner = viewer is not None and viewer.id == user.id
    out = UserPublicOut.model_validate(user)
    out.email = user.email if (is_owner or user.show_email) else None
    return out


@router.get("/search", response_model=list[UserPublicOut])
async def search_users(
    q: str = Query(..., min_length=1, max_length=30),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    result = await db.execute(
        select(User)
        .where(
            or_(
                User.nickname.ilike(f"%{q}%"),
                and_(User.show_email == True, User.email.ilike(f"%{q}%")),
            )
        )
        .order_by(User.id)
        .limit(limit)
    )
    return [_build_public_out(u, current_user) for u in result.scalars().all()]


@router.put("/me/show-email")
async def update_show_email(
    payload: ShowEmailUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.show_email = payload.show_email
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return {"show_email": current_user.show_email}


@router.get("/{user_id}", response_model=UserPublicOut)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return _build_public_out(user, current_user)


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    is_owner = current_user is not None and current_user.id == user_id
    filters = [Checkin.user_id == user_id]
    if not is_owner:
        filters.append(Checkin.is_public == True)

    # Total checkins
    result = await db.execute(
        select(func.count(Checkin.id)).where(*filters)
    )
    total_checkins = result.scalar() or 0

    # Total unique places
    result = await db.execute(
        select(
            func.count(
                func.distinct(
                    func.printf(
                        "%.5f:%.5f:%s",
                        Checkin.latitude,
                        Checkin.longitude,
                        Checkin.location_name,
                    )
                )
            )
        ).where(*filters)
    )
    total_places = result.scalar() or 0

    # Total photos
    result = await db.execute(
        select(func.count(Photo.id))
        .join(Checkin, Photo.checkin_id == Checkin.id)
        .where(*filters)
    )
    total_photos = result.scalar() or 0

    return UserStats(
        total_checkins=total_checkins,
        total_places=total_places,
        total_photos=total_photos,
    )


@router.put("/me/avatar")
async def update_avatar(
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content = await avatar.read()
        normalized_bytes, extension = prepare_uploaded_image(avatar.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}{extension}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(normalized_bytes)

    current_user.avatar_url = f"/uploads/{filename}"
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return {"avatar_url": current_user.avatar_url}
