from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import List, Optional, Set, Dict, Tuple
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update as sa_update
from app.models.checkin import Checkin as CheckinModel

from app.core.config import settings
from app.core.deps import get_db, get_current_user, get_optional_user
from app.crud.checkin import (
    create_checkin, add_photo_to_checkin,
    get_checkin_by_id, get_checkins_by_place, get_checkins_by_user,
    get_photos_by_place, get_public_map_checkins,
)
from app.schemas.checkin import CheckinMapItem, CheckinOut, PhotoOut, ReverseGeocodeOut, PlaceSearchOut
from app.models.user import User
from app.models.social import Like, Comment
from app.services.geocoding import reverse_geocode_coordinates, search_places_globally
from app.services.image_upload import prepare_uploaded_image
from app.services.region_normalizer import normalize_city_name, normalize_region_text
from app.services.video_compress import compress_video
from app.services.city_intro import ensure_city_intro
from app.services.footprint_report import ensure_footprint_report

router = APIRouter(prefix="/api/checkins", tags=["checkins"])


class CheckinUpdate(BaseModel):
    content: Optional[str] = None
    is_public: Optional[bool] = None


def _preview_text(content: Optional[str], max_length: int = 96) -> Optional[str]:
    if not content:
        return None
    cleaned = content.strip()
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 1]}…"


def _checkin_to_out(
    checkin,
    likes_count: int = 0,
    comments_count: int = 0,
    is_liked: bool = False,
) -> CheckinOut:
    return CheckinOut(
        id=checkin.id,
        user_id=checkin.user_id,
        place_id=checkin.place_id,
        location_name=checkin.location_name,
        city=normalize_city_name(checkin.city),
        address=normalize_region_text(checkin.address),
        latitude=checkin.latitude,
        longitude=checkin.longitude,
        content=checkin.content,
        visit_date=checkin.visit_date,
        is_public=checkin.is_public,
        created_at=checkin.created_at,
        photos=[PhotoOut.model_validate(p) for p in checkin.photos],
        user_nickname=checkin.user.nickname if checkin.user else "",
        user_avatar=checkin.user.avatar_url if checkin.user else None,
        place_name=checkin.place.name if checkin.place else checkin.location_name,
        likes_count=likes_count,
        comments_count=comments_count,
        is_liked=is_liked,
        media_type=checkin.media_type or "photo",
        video_url=checkin.video_url,
    )


def _checkin_to_map_item(checkin, likes_count: int = 0, comments_count: int = 0) -> CheckinMapItem:
    preview_image = checkin.photos[0].image_url if checkin.photos else None
    return CheckinMapItem(
        id=checkin.id,
        user_id=checkin.user_id,
        user_nickname=checkin.user.nickname if checkin.user else "",
        user_avatar=checkin.user.avatar_url if checkin.user else None,
        location_name=checkin.location_name,
        city=normalize_city_name(checkin.city),
        address=normalize_region_text(checkin.address),
        latitude=checkin.latitude,
        longitude=checkin.longitude,
        preview_text=_preview_text(checkin.content),
        preview_image_url=preview_image,
        photo_count=len(checkin.photos),
        visit_date=checkin.visit_date,
        created_at=checkin.created_at,
        likes_count=likes_count,
        comments_count=comments_count,
        is_liked=False,
        media_type=checkin.media_type or "photo",
        video_url=checkin.video_url,
    )


def _can_view_checkin(checkin, current_user: Optional[User]) -> bool:
    if checkin.is_public:
        return True
    return current_user is not None and current_user.id == checkin.user_id


def _resolve_uploaded_photo_path(image_url: Optional[str]) -> Optional[Path]:
    if not image_url:
        return None

    filename = os.path.basename(image_url)
    if not filename:
        return None

    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    candidate = (upload_dir / filename).resolve()

    try:
        candidate.relative_to(upload_dir)
    except ValueError:
        return None

    return candidate


async def _get_checkin_social_maps(
    db: AsyncSession,
    checkin_ids: List[int],
    current_user: Optional[User] = None,
) -> Tuple[Dict[int, int], Dict[int, int], Set[int]]:
    if not checkin_ids:
        return {}, {}, set()

    likes_result = await db.execute(
        select(Like.checkin_id, func.count(Like.id).label("cnt"))
        .where(Like.checkin_id.in_(checkin_ids))
        .group_by(Like.checkin_id)
    )
    likes_map = {row.checkin_id: row.cnt for row in likes_result.all()}

    comments_result = await db.execute(
        select(Comment.checkin_id, func.count(Comment.id).label("cnt"))
        .where(Comment.checkin_id.in_(checkin_ids))
        .group_by(Comment.checkin_id)
    )
    comments_map = {row.checkin_id: row.cnt for row in comments_result.all()}

    liked_ids: Set[int] = set()
    if current_user is not None:
        liked_result = await db.execute(
            select(Like.checkin_id)
            .where(
                Like.user_id == current_user.id,
                Like.checkin_id.in_(checkin_ids),
            )
        )
        liked_ids = {row.checkin_id for row in liked_result.all()}

    return likes_map, comments_map, liked_ids


@router.get("/map", response_model=List[CheckinMapItem])
async def list_public_map_checkins(
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    checkins = await get_public_map_checkins(db, limit)
    if not checkins:
        return []

    checkin_ids = [c.id for c in checkins]

    # Batch-fetch likes counts
    likes_result = await db.execute(
        select(Like.checkin_id, func.count(Like.id).label("cnt"))
        .where(Like.checkin_id.in_(checkin_ids))
        .group_by(Like.checkin_id)
    )
    likes_map = {row.checkin_id: row.cnt for row in likes_result.all()}

    # Batch-fetch comments counts
    comments_result = await db.execute(
        select(Comment.checkin_id, func.count(Comment.id).label("cnt"))
        .where(Comment.checkin_id.in_(checkin_ids))
        .group_by(Comment.checkin_id)
    )
    comments_map = {row.checkin_id: row.cnt for row in comments_result.all()}

    return [
        _checkin_to_map_item(
            checkin,
            likes_count=likes_map.get(checkin.id, 0),
            comments_count=comments_map.get(checkin.id, 0),
        )
        for checkin in checkins
    ]


@router.get("/reverse-geocode", response_model=ReverseGeocodeOut)
async def reverse_geocode_checkin_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    result = await reverse_geocode_coordinates(latitude, longitude)
    return ReverseGeocodeOut(city=result.city, address=result.address)


@router.get("/search-places", response_model=List[PlaceSearchOut])
async def search_checkin_places(
    q: str = Query(..., min_length=1, description="地点关键词"),
    limit: int = Query(default=8, ge=1, le=10),
):
    results = await search_places_globally(q, limit)
    return [
        PlaceSearchOut(
            id=item.id,
            name=item.name,
            city=normalize_city_name(item.city),
            address=normalize_region_text(item.address),
            latitude=item.latitude,
            longitude=item.longitude,
        )
        for item in results
    ]


_ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
_MAX_VIDEO_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB


@router.post("", response_model=CheckinOut)
async def publish_checkin(
    location_name: Optional[str] = Form(default=None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    city: Optional[str] = Form(default=None),
    address: Optional[str] = Form(default=None),
    content: Optional[str] = Form(default=None),
    is_public: bool = Form(True),
    media_type: str = Form(default="photo"),
    photos: List[UploadFile] = File(default=[]),
    video: Optional[UploadFile] = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cleaned_name = (location_name or "").strip() or city or address or "打卡"

    resolved_media_type = "video" if media_type == "video" and video is not None else "photo"

    prepared_photos: List[Tuple[int, bytes, str]] = []
    if resolved_media_type == "photo":
        for idx, photo_file in enumerate(photos):
            try:
                content_bytes = await photo_file.read()
                # Run PIL processing in a thread to avoid blocking the event loop
                normalized_bytes, extension = await asyncio.to_thread(
                    prepare_uploaded_image, photo_file.filename, content_bytes
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            prepared_photos.append((idx, normalized_bytes, extension))
    else:
        # For video checkins, photos list contains the thumbnail (first frame)
        for idx, photo_file in enumerate(photos):
            try:
                content_bytes = await photo_file.read()
                normalized_bytes, extension = await asyncio.to_thread(
                    prepare_uploaded_image, photo_file.filename, content_bytes
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            prepared_photos.append((idx, normalized_bytes, extension))

    # Keep visit_date aligned with publish time so the client no longer needs
    # a separate manual date selector.
    parsed_date = datetime.now(timezone.utc).date()

    cleaned_city = normalize_city_name(city.strip()) if city and city.strip() else None
    cleaned_address = normalize_region_text(address.strip()) if address and address.strip() else None

    if not cleaned_city or not cleaned_address:
        detected_location = await reverse_geocode_coordinates(latitude, longitude)
        if not cleaned_city and detected_location.city:
            cleaned_city = normalize_city_name(detected_location.city)
        if not cleaned_address and detected_location.address:
            cleaned_address = normalize_region_text(detected_location.address)

    # Create checkin
    checkin = await create_checkin(
        db,
        user_id=current_user.id,
        location_name=cleaned_name,
        latitude=latitude,
        longitude=longitude,
        city=cleaned_city,
        address=cleaned_address,
        content=content,
        visit_date=parsed_date,
        is_public=is_public,
        media_type=resolved_media_type,
    )

    # Save photos / thumbnail (file I/O in thread to avoid blocking the event loop)
    def _write_file(path: str, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)

    for idx, content_bytes, extension in prepared_photos:
        filename = f"{uuid.uuid4().hex}{extension}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)

        await asyncio.to_thread(_write_file, filepath, content_bytes)

        await add_photo_to_checkin(
            db, checkin_id=checkin.id,
            image_url=f"/uploads/{filename}",
            sort_order=idx,
        )

    # Save video file if provided (with compression)
    if resolved_media_type == "video" and video is not None:
        video_bytes = await video.read()
        if len(video_bytes) > _MAX_VIDEO_SIZE_BYTES:
            raise HTTPException(status_code=422, detail="视频文件不能超过 200MB")

        original_filename = video.filename or "video.mp4"

        # Compress video in a thread (CPU-bound, blocks event loop if called directly)
        try:
            compressed_bytes, video_ext = await asyncio.to_thread(
                compress_video, video_bytes, original_filename
            )
        except ValueError as exc:
            # Compression failed: fall back to storing original with safe extension
            raw_ext = os.path.splitext(original_filename)[1].lower()
            if raw_ext not in _ALLOWED_VIDEO_EXTENSIONS:
                raw_ext = ".mp4"
            compressed_bytes = video_bytes
            video_ext = raw_ext

        video_filename = f"{uuid.uuid4().hex}{video_ext}"
        video_filepath = os.path.join(settings.UPLOAD_DIR, video_filename)
        await asyncio.to_thread(_write_file, video_filepath, compressed_bytes)

        # Update checkin with video_url via direct SQL update
        await db.execute(
            sa_update(CheckinModel)
            .where(CheckinModel.id == checkin.id)
            .values(video_url=f"/uploads/{video_filename}")
        )
        await db.commit()

    checkin = await get_checkin_by_id(db, checkin.id)
    if cleaned_city:
        ensure_city_intro(cleaned_city)
    ensure_footprint_report(current_user.id)
    return _checkin_to_out(checkin)


@router.get("/place/{place_id}", response_model=List[CheckinOut])
async def list_place_checkins(
    place_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    checkins = await get_checkins_by_place(db, place_id, limit, offset)
    return [_checkin_to_out(c) for c in checkins]


@router.get("/user/{user_id}", response_model=List[CheckinOut])
async def list_user_checkins(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    include_private = current_user is not None and current_user.id == user_id
    checkins = await get_checkins_by_user(db, user_id, include_private, limit, offset)
    likes_map, comments_map, liked_ids = await _get_checkin_social_maps(
        db,
        [checkin.id for checkin in checkins],
        current_user=current_user,
    )
    return [
        _checkin_to_out(
            checkin,
            likes_count=likes_map.get(checkin.id, 0),
            comments_count=comments_map.get(checkin.id, 0),
            is_liked=checkin.id in liked_ids,
        )
        for checkin in checkins
    ]


@router.get("/place/{place_id}/photos", response_model=List[PhotoOut])
async def list_place_photos(
    place_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    photos = await get_photos_by_place(db, place_id, limit)
    return [PhotoOut.model_validate(p) for p in photos]


@router.get("/{checkin_id}", response_model=CheckinOut)
async def get_checkin_detail(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    checkin = await get_checkin_by_id(db, checkin_id)
    if not checkin or not _can_view_checkin(checkin, current_user):
        raise HTTPException(status_code=404, detail="打卡不存在")
    likes_map, comments_map, liked_ids = await _get_checkin_social_maps(
        db,
        [checkin.id],
        current_user=current_user,
    )
    return _checkin_to_out(
        checkin,
        likes_count=likes_map.get(checkin.id, 0),
        comments_count=comments_map.get(checkin.id, 0),
        is_liked=checkin.id in liked_ids,
    )


@router.delete("/{checkin_id}", status_code=200)
async def delete_user_checkin(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkin = await get_checkin_by_id(db, checkin_id)
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡不存在")
    if checkin.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的打卡")

    photo_paths = [
        resolved_path
        for resolved_path in (
            _resolve_uploaded_photo_path(photo.image_url)
            for photo in checkin.photos
        )
        if resolved_path is not None
    ]

    await db.delete(checkin)
    await db.commit()

    for photo_path in photo_paths:
        try:
            if photo_path.exists():
                photo_path.unlink()
        except OSError:
            continue


@router.patch("/{checkin_id}", response_model=CheckinOut)
async def update_checkin(
    checkin_id: int,
    body: CheckinUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    checkin = await get_checkin_by_id(db, checkin_id)
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡不存在")
    if checkin.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己的打卡")

    if body.content is not None:
        checkin.content = body.content.strip() if body.content.strip() else None
    if body.is_public is not None:
        checkin.is_public = body.is_public

    await db.commit()
    checkin = await get_checkin_by_id(db, checkin_id)
    return _checkin_to_out(checkin)

    return {"detail": "打卡已删除"}
