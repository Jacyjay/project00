from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.deps import get_db, get_current_user, get_optional_user
from app.models.user import User
from app.models.achievement import Achievement, UserAchievement
from app.schemas.achievement import AchievementWithStatus, UpdateVisibilityRequest
from app.services.achievements import get_user_unlocked_codes

router = APIRouter(prefix="/api/achievements", tags=["achievements"])


@router.get("", response_model=List[AchievementWithStatus])
async def list_all_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """获取所有成就定义及当前用户的解锁状态"""
    # 获取所有成就定义
    result = await db.execute(
        select(Achievement).order_by(Achievement.sort_order, Achievement.id)
    )
    achievements = result.scalars().all()

    # 如果用户已登录，获取解锁状态
    user_achievements_map = {}
    if current_user:
        unlocked_result = await db.execute(
            select(UserAchievement).where(UserAchievement.user_id == current_user.id)
        )
        for ua in unlocked_result.scalars().all():
            user_achievements_map[ua.achievement_code] = ua

    # 组装响应
    response = []
    for ach in achievements:
        ua = user_achievements_map.get(ach.code)
        response.append(
            AchievementWithStatus(
                id=ach.id,
                code=ach.code,
                name=ach.name,
                description=ach.description,
                icon=ach.icon,
                category=ach.category,
                rarity=ach.rarity,
                sort_order=ach.sort_order,
                created_at=ach.created_at,
                unlocked=ua is not None,
                unlocked_at=ua.unlocked_at if ua else None,
                is_visible=ua.is_visible if ua else None,
            )
        )

    return response


@router.get("/users/{user_id}", response_model=List[AchievementWithStatus])
async def get_user_achievements(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """获取指定用户的成就（仅显示公开的，除非是本人）"""
    is_own = current_user and current_user.id == user_id

    # 获取用户的成就
    query = select(UserAchievement).where(UserAchievement.user_id == user_id)
    if not is_own:
        query = query.where(UserAchievement.is_visible == True)

    result = await db.execute(query)
    user_achievements = result.scalars().all()

    # 获取成就定义
    codes = [ua.achievement_code for ua in user_achievements]
    if not codes:
        return []

    ach_result = await db.execute(
        select(Achievement).where(Achievement.code.in_(codes))
    )
    achievements_map = {ach.code: ach for ach in ach_result.scalars().all()}

    # 组装响应
    response = []
    for ua in user_achievements:
        ach = achievements_map.get(ua.achievement_code)
        if ach:
            response.append(
                AchievementWithStatus(
                    id=ach.id,
                    code=ach.code,
                    name=ach.name,
                    description=ach.description,
                    icon=ach.icon,
                    category=ach.category,
                    rarity=ach.rarity,
                    sort_order=ach.sort_order,
                    created_at=ach.created_at,
                    unlocked=True,
                    unlocked_at=ua.unlocked_at,
                    is_visible=ua.is_visible if is_own else None,
                )
            )

    # 按解锁时间倒序
    response.sort(key=lambda x: x.unlocked_at, reverse=True)
    return response


@router.put("/me/{achievement_code}/visibility")
async def update_achievement_visibility(
    achievement_code: str,
    body: UpdateVisibilityRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新成就可见性"""
    result = await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == current_user.id,
            UserAchievement.achievement_code == achievement_code,
        )
    )
    user_achievement = result.scalar_one_or_none()

    if not user_achievement:
        raise HTTPException(status_code=404, detail="成就未解锁")

    user_achievement.is_visible = body.is_visible
    await db.commit()

    return {"achievement_code": achievement_code, "is_visible": body.is_visible}


@router.get("/stats")
async def get_achievement_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的成就统计"""
    # 总成就数
    total_result = await db.execute(select(func.count(Achievement.id)))
    total = total_result.scalar_one()

    # 已解锁数
    unlocked_result = await db.execute(
        select(func.count(UserAchievement.id)).where(
            UserAchievement.user_id == current_user.id
        )
    )
    unlocked = unlocked_result.scalar_one()

    # 按稀有度统计
    rarity_result = await db.execute(
        select(Achievement.rarity, func.count(UserAchievement.id))
        .join(UserAchievement, Achievement.code == UserAchievement.achievement_code)
        .where(UserAchievement.user_id == current_user.id)
        .group_by(Achievement.rarity)
    )
    rarity_stats = {row[0]: row[1] for row in rarity_result.all()}

    return {
        "total": total,
        "unlocked": unlocked,
        "progress_percentage": round((unlocked / total * 100) if total > 0 else 0, 1),
        "by_rarity": rarity_stats,
    }
