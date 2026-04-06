from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, date, timedelta
from typing import Optional
from app.core.deps import get_db, get_current_user, get_current_user_optional
from app.models.social import Like, Comment
from app.models.checkin import Checkin
from app.models.user import User
from app.models.photo import Photo
from app.services.city_intro import ensure_city_intro, get_city_intro
from pydantic import BaseModel

router = APIRouter()

# ─── schemas ───────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str

class CommentOut(BaseModel):
    id: int
    user_id: int
    checkin_id: int
    content: str
    created_at: datetime
    user_nickname: Optional[str] = None
    user_avatar: Optional[str] = None

    class Config:
        from_attributes = True

# ─── Like endpoints ────────────────────────────────────────────────────────

@router.post("/checkins/{checkin_id}/like", status_code=200)
async def like_checkin(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check checkin exists and is public
    result = await db.execute(select(Checkin).where(Checkin.id == checkin_id, Checkin.is_public == True))
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")

    # Check if already liked
    result = await db.execute(
        select(Like).where(Like.user_id == current_user.id, Like.checkin_id == checkin_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"liked": True, "likes_count": await _get_likes_count(db, checkin_id)}

    like = Like(user_id=current_user.id, checkin_id=checkin_id)
    db.add(like)
    await db.commit()
    count = await _get_likes_count(db, checkin_id)
    return {"liked": True, "likes_count": count}


@router.delete("/checkins/{checkin_id}/like", status_code=200)
async def unlike_checkin(
    checkin_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Like).where(Like.user_id == current_user.id, Like.checkin_id == checkin_id)
    )
    like = result.scalar_one_or_none()
    if like:
        await db.delete(like)
        await db.commit()
    count = await _get_likes_count(db, checkin_id)
    return {"liked": False, "likes_count": count}


async def _get_likes_count(db: AsyncSession, checkin_id: int) -> int:
    result = await db.execute(select(func.count()).where(Like.checkin_id == checkin_id))
    return result.scalar() or 0

# ─── Comment endpoints ─────────────────────────────────────────────────────

@router.get("/checkins/{checkin_id}/comments")
async def get_comments(
    checkin_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Comment, User.nickname, User.avatar_url)
        .join(User, Comment.user_id == User.id)
        .where(Comment.checkin_id == checkin_id)
        .order_by(Comment.created_at.asc())
    )
    rows = result.all()
    comments = []
    for comment, nickname, avatar_url in rows:
        comments.append({
            "id": comment.id,
            "user_id": comment.user_id,
            "checkin_id": comment.checkin_id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "user_nickname": nickname,
            "user_avatar": avatar_url
        })
    return {"comments": comments, "total": len(comments)}


@router.post("/checkins/{checkin_id}/comments")
async def add_comment(
    checkin_id: int,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not body.content or len(body.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="评论内容不能为空")
    if len(body.content) > 500:
        raise HTTPException(status_code=400, detail="评论内容不能超过500字")

    result = await db.execute(select(Checkin).where(Checkin.id == checkin_id, Checkin.is_public == True))
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=404, detail="打卡记录不存在")

    comment = Comment(user_id=current_user.id, checkin_id=checkin_id, content=body.content.strip())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "checkin_id": comment.checkin_id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "user_nickname": current_user.nickname,
        "user_avatar": current_user.avatar_url
    }

@router.delete("/checkins/{checkin_id}/comments/{comment_id}", status_code=200)
async def delete_comment(
    checkin_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.checkin_id == checkin_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能删除自己的评论")
    await db.delete(comment)
    await db.commit()
    return {"deleted": True}


# ─── Hot Cities ────────────────────────────────────────────────────────────

@router.get("/cities/hot")
async def get_hot_cities(db: AsyncSession = Depends(get_db)):
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)  # naive datetime for SQLite
    today_end = today_start + timedelta(days=1)

    # Today hot cities (top 5)
    today_result = await db.execute(
        select(Checkin.city, func.count(Checkin.id).label("count"))
        .where(
            Checkin.is_public == True,
            Checkin.city != None,
            Checkin.city != "",
            Checkin.created_at >= today_start,
            Checkin.created_at < today_end
        )
        .group_by(Checkin.city)
        .order_by(desc("count"))
        .limit(5)
    )
    today_cities = [
        {"city": row.city, "count": row.count, "intro": get_city_intro(row.city)}
        for row in today_result.all()
    ]

    # Historical hot cities (top 5, all time)
    hist_result = await db.execute(
        select(Checkin.city, func.count(Checkin.id).label("count"))
        .where(
            Checkin.is_public == True,
            Checkin.city != None,
            Checkin.city != ""
        )
        .group_by(Checkin.city)
        .order_by(desc("count"))
        .limit(5)
    )
    hist_cities = [
        {"city": row.city, "count": row.count, "intro": get_city_intro(row.city)}
        for row in hist_result.all()
    ]

    # Trigger background generation for any city not yet cached
    all_cities = {item["city"] for item in today_cities + hist_cities}
    for city in all_cities:
        ensure_city_intro(city)

    return {"today": today_cities, "historical": hist_cities}


@router.get("/cities/{city}/intro")
async def get_city_intro_endpoint(city: str):
    """Return the cached AI intro for a city. Triggers background generation if not yet cached."""
    intro = get_city_intro(city)
    ensure_city_intro(city)
    return {"city": city, "intro": intro}


@router.get("/cities/{city}/checkins")
async def get_city_checkins(
    city: str,
    sort: str = Query("latest", pattern="^(likes|comments|latest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    offset = (page - 1) * page_size

    # Build base query
    if sort == "likes":
        stmt = (
            select(Checkin, User.nickname, User.avatar_url, func.count(Like.id).label("likes_count"))
            .join(User, Checkin.user_id == User.id)
            .outerjoin(Like, Like.checkin_id == Checkin.id)
            .where(Checkin.is_public == True, Checkin.city == city)
            .group_by(Checkin.id, User.nickname, User.avatar_url)
            .order_by(desc("likes_count"), desc(Checkin.created_at))
        )
    elif sort == "comments":
        stmt = (
            select(Checkin, User.nickname, User.avatar_url, func.count(Comment.id).label("comments_count"))
            .join(User, Checkin.user_id == User.id)
            .outerjoin(Comment, Comment.checkin_id == Checkin.id)
            .where(Checkin.is_public == True, Checkin.city == city)
            .group_by(Checkin.id, User.nickname, User.avatar_url)
            .order_by(desc("comments_count"), desc(Checkin.created_at))
        )
    else:  # latest
        stmt = (
            select(Checkin, User.nickname, User.avatar_url)
            .join(User, Checkin.user_id == User.id)
            .where(Checkin.is_public == True, Checkin.city == city)
            .order_by(desc(Checkin.created_at))
        )

    # Count total
    count_stmt = select(func.count()).select_from(
        select(Checkin.id).where(Checkin.is_public == True, Checkin.city == city).subquery()
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    result = await db.execute(stmt.offset(offset).limit(page_size))
    rows = result.all()

    if not rows:
        return {"checkins": [], "total": total, "page": page, "page_size": page_size}

    checkin_ids = [row[0].id for row in rows]

    # Batch-fetch first photo per checkin
    photos_result = await db.execute(
        select(Photo.checkin_id, Photo.image_url)
        .where(Photo.checkin_id.in_(checkin_ids))
        .order_by(Photo.checkin_id, Photo.sort_order)
    )
    first_photo_map: dict[int, str] = {}
    for cid, img_url in photos_result.all():
        if cid not in first_photo_map:
            first_photo_map[cid] = img_url

    # Batch-fetch likes counts
    likes_cnt_result = await db.execute(
        select(Like.checkin_id, func.count(Like.id).label("cnt"))
        .where(Like.checkin_id.in_(checkin_ids))
        .group_by(Like.checkin_id)
    )
    likes_map = {row.checkin_id: row.cnt for row in likes_cnt_result.all()}

    # Batch-fetch comments counts
    comments_cnt_result = await db.execute(
        select(Comment.checkin_id, func.count(Comment.id).label("cnt"))
        .where(Comment.checkin_id.in_(checkin_ids))
        .group_by(Comment.checkin_id)
    )
    comments_map = {row.checkin_id: row.cnt for row in comments_cnt_result.all()}

    # Batch-fetch liked ids for current user
    liked_ids: set[int] = set()
    if current_user:
        liked_result = await db.execute(
            select(Like.checkin_id)
            .where(Like.user_id == current_user.id, Like.checkin_id.in_(checkin_ids))
        )
        liked_ids = {row.checkin_id for row in liked_result.all()}

    checkins = []
    for row in rows:
        checkin = row[0]
        nickname = row[1]
        avatar_url = row[2]
        checkins.append({
            "id": checkin.id,
            "user_id": checkin.user_id,
            "user_nickname": nickname,
            "user_avatar": avatar_url,
            "location_name": checkin.location_name,
            "city": checkin.city,
            "content": checkin.content,
            "visit_date": checkin.visit_date.isoformat() if checkin.visit_date else None,
            "created_at": checkin.created_at.isoformat(),
            "first_photo": first_photo_map.get(checkin.id),
            "likes_count": likes_map.get(checkin.id, 0),
            "comments_count": comments_map.get(checkin.id, 0),
            "is_liked": checkin.id in liked_ids,
        })

    return {"checkins": checkins, "total": total, "page": page, "page_size": page_size}
