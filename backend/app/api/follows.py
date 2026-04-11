from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.core.deps import get_db, get_current_user, get_optional_user
from app.models.follow import Follow
from app.models.user import User
from app.models.checkin import Checkin
from app.models.social import Like, Comment
from app.services.achievements import ensure_achievements_check

router = APIRouter(prefix="/api", tags=["follows"])


# ── Follow / Unfollow ──────────────────────────────────────────────────────────

@router.post("/users/{user_id}/follow")
async def follow_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    existing = (await db.execute(
        select(Follow).where(and_(Follow.follower_id == current_user.id, Follow.following_id == user_id))
    )).scalar_one_or_none()
    if existing:
        return {"status": "already_following"}
    db.add(Follow(follower_id=current_user.id, following_id=user_id))
    await db.commit()

    # 关注行为触发双方成就检测（如社交达人）
    ensure_achievements_check(current_user.id, "follow")
    ensure_achievements_check(user_id, "follow")

    return {"status": "following"}


@router.delete("/users/{user_id}/follow")
async def unfollow_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    follow = (await db.execute(
        select(Follow).where(and_(Follow.follower_id == current_user.id, Follow.following_id == user_id))
    )).scalar_one_or_none()
    if follow:
        await db.delete(follow)
        await db.commit()
    return {"status": "unfollowed"}


# ── Follow status & counts ─────────────────────────────────────────────────────

@router.get("/users/{user_id}/follow-status")
async def get_follow_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    followers_count = (await db.execute(
        select(func.count(Follow.id)).where(Follow.following_id == user_id)
    )).scalar_one()
    following_count = (await db.execute(
        select(func.count(Follow.id)).where(Follow.follower_id == user_id)
    )).scalar_one()

    if not current_user or current_user.id == user_id:
        return {
            "is_following": False,
            "is_mutual": False,
            "followers_count": followers_count,
            "following_count": following_count,
        }

    is_following = (await db.execute(
        select(Follow).where(and_(Follow.follower_id == current_user.id, Follow.following_id == user_id))
    )).scalar_one_or_none() is not None

    is_followed_back = (await db.execute(
        select(Follow).where(and_(Follow.follower_id == user_id, Follow.following_id == current_user.id))
    )).scalar_one_or_none() is not None

    return {
        "is_following": is_following,
        "is_mutual": is_following and is_followed_back,
        "followers_count": followers_count,
        "following_count": following_count,
    }


# ── Feed（关注用户的打卡动态）──────────────────────────────────────────────────

@router.get("/feed")
async def get_feed(
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    following_ids = [
        row[0] for row in (await db.execute(
            select(Follow.following_id).where(Follow.follower_id == current_user.id)
        )).all()
    ]

    if not following_ids:
        return {"checkins": [], "total": 0, "has_more": False}

    where = and_(Checkin.user_id.in_(following_ids), Checkin.is_public == True)

    total = (await db.execute(select(func.count(Checkin.id)).where(where))).scalar_one()

    checkins = (await db.execute(
        select(Checkin)
        .where(where)
        .options(selectinload(Checkin.user), selectinload(Checkin.photos))
        .order_by(Checkin.created_at.desc())
        .limit(limit)
        .offset(offset)
    )).scalars().all()

    result = []
    for c in checkins:
        likes_count = (await db.execute(
            select(func.count(Like.id)).where(Like.checkin_id == c.id)
        )).scalar_one()
        comments_count = (await db.execute(
            select(func.count(Comment.id)).where(Comment.checkin_id == c.id)
        )).scalar_one()
        is_liked = (await db.execute(
            select(Like).where(and_(Like.user_id == current_user.id, Like.checkin_id == c.id))
        )).scalar_one_or_none() is not None

        preview_image = c.photos[0].image_url if c.photos else None

        result.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_nickname": c.user.nickname if c.user else "",
            "user_avatar": c.user.avatar_url if c.user else None,
            "location_name": c.location_name,
            "city": c.city,
            "address": c.address,
            "content": c.content,
            "preview_image_url": preview_image,
            "media_type": c.media_type,
            "photo_count": len(c.photos),
            "likes_count": likes_count,
            "comments_count": comments_count,
            "is_liked": is_liked,
            "is_public": c.is_public,
            "visit_date": c.visit_date.isoformat() if c.visit_date else None,
            "created_at": c.created_at.replace(tzinfo=timezone.utc).isoformat(),
        })

    return {"checkins": result, "total": total, "has_more": offset + limit < total}


# ── Mutual followers（用于私信列表自动合并）────────────────────────────────────

@router.get("/follows/mutual")
async def get_mutual_followers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回与当前用户互相关注的用户列表"""
    following_ids = [
        row[0] for row in (await db.execute(
            select(Follow.following_id).where(Follow.follower_id == current_user.id)
        )).all()
    ]
    if not following_ids:
        return []

    # Of those, which ones also follow current_user back?
    mutual_ids = [
        row[0] for row in (await db.execute(
            select(Follow.follower_id).where(
                and_(Follow.follower_id.in_(following_ids), Follow.following_id == current_user.id)
            )
        )).all()
    ]
    if not mutual_ids:
        return []

    users = (await db.execute(
        select(User).where(User.id.in_(mutual_ids))
    )).scalars().all()

    return [{"id": u.id, "nickname": u.nickname, "avatar_url": u.avatar_url} for u in users]


# ── Followers list ─────────────────────────────────────────────────────────────

@router.get("/users/{user_id}/followers")
async def get_followers(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    is_own = current_user and current_user.id == user_id
    if not target.show_followers and not is_own:
        raise HTTPException(status_code=403, detail="该用户已设置粉丝列表不公开")

    rows = (await db.execute(
        select(Follow.follower_id).where(Follow.following_id == user_id)
    )).all()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    users = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return [{"id": u.id, "nickname": u.nickname, "avatar_url": u.avatar_url} for u in users]


# ── Following list ─────────────────────────────────────────────────────────────

@router.get("/users/{user_id}/following")
async def get_following(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    is_own = current_user and current_user.id == user_id
    if not target.show_following and not is_own:
        raise HTTPException(status_code=403, detail="该用户已设置关注列表不公开")

    rows = (await db.execute(
        select(Follow.following_id).where(Follow.follower_id == user_id)
    )).all()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    users = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return [{"id": u.id, "nickname": u.nickname, "avatar_url": u.avatar_url} for u in users]


# ── Follow privacy settings ────────────────────────────────────────────────────

@router.put("/users/me/follow-privacy")
async def update_follow_privacy(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if "show_followers" in data:
        current_user.show_followers = bool(data["show_followers"])
    if "show_following" in data:
        current_user.show_following = bool(data["show_following"])
    db.add(current_user)
    await db.commit()
    return {"show_followers": current_user.show_followers, "show_following": current_user.show_following}
