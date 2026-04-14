"""
成就系统服务 - 成就检测和解锁逻辑
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, time
from typing import List, Optional, Set

from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.achievement import Achievement, UserAchievement
from app.models.checkin import Checkin
from app.models.social import Like, Comment
from app.models.user import User

logger = logging.getLogger(__name__)

# 成就定义（Phase 1 MVP - 10个基础成就）
ACHIEVEMENT_DEFINITIONS = [
    # 探索类
    {
        "code": "first_trip",
        "name": "首次出游",
        "description": "完成第一次打卡",
        "icon": "🗺️",
        "category": "探索",
        "rarity": "common",
        "sort_order": 1,
    },
    {
        "code": "city_explorer",
        "name": "城市探索者",
        "description": "打卡5个不同城市",
        "icon": "🌍",
        "category": "探索",
        "rarity": "rare",
        "sort_order": 2,
    },
    {
        "code": "travel_master",
        "name": "旅行达人",
        "description": "打卡20个不同城市",
        "icon": "🌏",
        "category": "探索",
        "rarity": "epic",
        "sort_order": 3,
    },
    {
        "code": "checkin_milestone_10",
        "name": "足迹初现",
        "description": "完成10次打卡",
        "icon": "📍",
        "category": "探索",
        "rarity": "common",
        "sort_order": 4,
    },
    {
        "code": "checkin_milestone_50",
        "name": "足迹大师",
        "description": "完成50次打卡",
        "icon": "⭐",
        "category": "探索",
        "rarity": "epic",
        "sort_order": 5,
    },
    # 时间类
    {
        "code": "night_owl",
        "name": "夜游达人",
        "description": "晚上10点后打卡10次",
        "icon": "🌙",
        "category": "时间",
        "rarity": "rare",
        "sort_order": 6,
    },
    {
        "code": "early_bird",
        "name": "早起鸟",
        "description": "早上6点前打卡10次",
        "icon": "🌅",
        "category": "时间",
        "rarity": "rare",
        "sort_order": 7,
    },
    # 社交类
    {
        "code": "social_butterfly",
        "name": "社交达人",
        "description": "获得50个粉丝",
        "icon": "👥",
        "category": "社交",
        "rarity": "epic",
        "sort_order": 8,
    },
    # 内容类
    {
        "code": "content_creator",
        "name": "文案高手",
        "description": "发布20条带文案的打卡",
        "icon": "📝",
        "category": "内容",
        "rarity": "rare",
        "sort_order": 9,
    },
    {
        "code": "photographer",
        "name": "摄影师",
        "description": "上传50张照片",
        "icon": "📸",
        "category": "内容",
        "rarity": "rare",
        "sort_order": 10,
    },
]


async def init_achievements():
    """初始化成就定义到数据库"""
    async with async_session_maker() as db:
        for ach_def in ACHIEVEMENT_DEFINITIONS:
            existing = await db.execute(
                select(Achievement).where(Achievement.code == ach_def["code"])
            )
            if not existing.scalar_one_or_none():
                achievement = Achievement(**ach_def)
                db.add(achievement)
        await db.commit()
        logger.info(f"Initialized {len(ACHIEVEMENT_DEFINITIONS)} achievements")


async def get_user_unlocked_codes(db: AsyncSession, user_id: int) -> Set[str]:
    """获取用户已解锁的成就代码集合"""
    result = await db.execute(
        select(UserAchievement.achievement_code).where(UserAchievement.user_id == user_id)
    )
    return {row[0] for row in result.all()}


async def unlock_achievement(db: AsyncSession, user_id: int, achievement_code: str) -> bool:
    """解锁成就"""
    try:
        user_achievement = UserAchievement(
            user_id=user_id,
            achievement_code=achievement_code,
            unlocked_at=datetime.now(timezone.utc),
            is_visible=True,
        )
        db.add(user_achievement)
        await db.commit()
        logger.info(f"User {user_id} unlocked achievement: {achievement_code}")
        return True
    except Exception as e:
        logger.warning(f"Failed to unlock achievement {achievement_code} for user {user_id}: {e}")
        await db.rollback()
        return False


async def check_first_trip(db: AsyncSession, user_id: int) -> bool:
    """检测：首次出游"""
    result = await db.execute(
        select(func.count(Checkin.id)).where(Checkin.user_id == user_id)
    )
    count = result.scalar_one()
    return count >= 1


async def check_city_explorer(db: AsyncSession, user_id: int) -> bool:
    """检测：城市探索者（5个不同城市）"""
    result = await db.execute(
        select(func.count(distinct(Checkin.city)))
        .where(Checkin.user_id == user_id, Checkin.city.isnot(None), Checkin.city != "")
    )
    count = result.scalar_one()
    return count >= 5


async def check_travel_master(db: AsyncSession, user_id: int) -> bool:
    """检测：旅行达人（20个不同城市）"""
    result = await db.execute(
        select(func.count(distinct(Checkin.city)))
        .where(Checkin.user_id == user_id, Checkin.city.isnot(None), Checkin.city != "")
    )
    count = result.scalar_one()
    return count >= 20


async def check_checkin_milestone(db: AsyncSession, user_id: int, target: int) -> bool:
    """检测：打卡里程碑"""
    result = await db.execute(
        select(func.count(Checkin.id)).where(Checkin.user_id == user_id)
    )
    count = result.scalar_one()
    return count >= target


async def check_night_owl(db: AsyncSession, user_id: int) -> bool:
    """检测：夜游达人（晚上10点后打卡10次）"""
    result = await db.execute(
        select(Checkin).where(Checkin.user_id == user_id)
    )
    checkins = result.scalars().all()

    night_count = 0
    for checkin in checkins:
        hour = checkin.created_at.hour
        if hour >= 22 or hour < 6:  # 22:00-06:00
            night_count += 1

    return night_count >= 10


async def check_early_bird(db: AsyncSession, user_id: int) -> bool:
    """检测：早起鸟（早上6点前打卡10次）"""
    result = await db.execute(
        select(Checkin).where(Checkin.user_id == user_id)
    )
    checkins = result.scalars().all()

    early_count = 0
    for checkin in checkins:
        hour = checkin.created_at.hour
        if hour < 6:  # 00:00-06:00
            early_count += 1

    return early_count >= 10


async def check_social_butterfly(db: AsyncSession, user_id: int) -> bool:
    """检测：社交达人（50个粉丝）"""
    from app.models.follow import Follow
    result = await db.execute(
        select(func.count(Follow.id)).where(Follow.following_id == user_id)
    )
    count = result.scalar_one()
    return count >= 50


async def check_content_creator(db: AsyncSession, user_id: int) -> bool:
    """检测：文案高手（20条带文案的打卡）"""
    result = await db.execute(
        select(func.count(Checkin.id))
        .where(Checkin.user_id == user_id, Checkin.content.isnot(None), Checkin.content != "")
    )
    count = result.scalar_one()
    return count >= 20


async def check_photographer(db: AsyncSession, user_id: int) -> bool:
    """检测：摄影师（50张照片）"""
    from app.models.photo import Photo
    result = await db.execute(
        select(func.count(Photo.id))
        .join(Checkin, Photo.checkin_id == Checkin.id)
        .where(Checkin.user_id == user_id)
    )
    count = result.scalar_one()
    return count >= 50


# 成就检测规则映射
ACHIEVEMENT_CHECKERS = {
    "first_trip": check_first_trip,
    "city_explorer": check_city_explorer,
    "travel_master": check_travel_master,
    "checkin_milestone_10": lambda db, uid: check_checkin_milestone(db, uid, 10),
    "checkin_milestone_50": lambda db, uid: check_checkin_milestone(db, uid, 50),
    "night_owl": check_night_owl,
    "early_bird": check_early_bird,
    "social_butterfly": check_social_butterfly,
    "content_creator": check_content_creator,
    "photographer": check_photographer,
}


async def check_achievements(user_id: int, trigger_type: str = "checkin") -> List[str]:
    """
    检测并解锁成就

    Args:
        user_id: 用户ID
        trigger_type: 触发类型（checkin, follow, etc.）

    Returns:
        新解锁的成就代码列表
    """
    async with async_session_maker() as db:
        # 获取已解锁的成就
        unlocked_codes = await get_user_unlocked_codes(db, user_id)

        # 检测所有未解锁的成就
        newly_unlocked = []
        for code, checker in ACHIEVEMENT_CHECKERS.items():
            if code not in unlocked_codes:
                try:
                    if await checker(db, user_id):
                        if await unlock_achievement(db, user_id, code):
                            newly_unlocked.append(code)
                except Exception as e:
                    logger.error(f"Error checking achievement {code} for user {user_id}: {e}")

        return newly_unlocked


async def backfill_achievements_for_all_users() -> None:
    """为历史用户回填成就，避免上线前老数据全灰。"""
    async with async_session_maker() as db:
        result = await db.execute(select(User.id))
        user_ids = [row[0] for row in result.all()]

    if not user_ids:
        return

    logger.info("Achievement backfill started for %d users", len(user_ids))
    for uid in user_ids:
        try:
            unlocked = await check_achievements(uid, "backfill")
            if unlocked:
                logger.info("Backfill unlocked for user %s: %s", uid, ",".join(unlocked))
        except Exception as exc:
            logger.warning("Backfill failed for user %s: %s", uid, exc)


def ensure_achievements_check(user_id: int, trigger_type: str = "checkin") -> None:
    """异步触发成就检测（不阻塞主流程）"""
    asyncio.create_task(check_achievements(user_id, trigger_type))
