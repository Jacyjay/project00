from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Set

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.checkin import Checkin
from app.models.photo import Photo
from app.models.footprint_report import FootprintReport

logger = logging.getLogger(__name__)

DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# user_ids currently being generated, to prevent duplicate concurrent requests
_GENERATING: Set[int] = set()


async def _generate_report(user_id: int) -> None:
    """Call Doubao AI and persist the result in footprint_reports table."""
    api_key = settings.DOUBAO_API_KEY
    endpoint_id = settings.DOUBAO_ENDPOINT_ID
    if not api_key or not endpoint_id:
        _GENERATING.discard(user_id)
        return

    try:
        async with async_session_maker() as db:
            # Fetch all checkins for this user (no limit, ordered by date)
            result = await db.execute(
                select(Checkin)
                .where(Checkin.user_id == user_id)
                .order_by(Checkin.created_at.desc())
            )
            checkins = result.scalars().all()

            if not checkins:
                _GENERATING.discard(user_id)
                return

            # Gather cities and contents
            cities_seen: list[str] = []
            cities_set: set[str] = set()
            checkin_lines: list[str] = []

            for c in checkins:
                if c.city and c.city not in cities_set:
                    cities_set.add(c.city)
                    cities_seen.append(c.city)

            # Build text summary (use up to 30 most recent checkins with content)
            count_with_content = 0
            for c in checkins:
                if count_with_content >= 30:
                    break
                city_label = f"[{c.city}] " if c.city else ""
                content_line = c.content.strip() if c.content else ""
                if not content_line:
                    continue
                checkin_lines.append(f"· {city_label}{c.location_name}：{content_line[:80]}")
                count_with_content += 1

            total = len(checkins)
            city_count = len(cities_seen)
            cities_str = "、".join(cities_seen[:20]) + ("…" if city_count > 20 else "")

            if checkin_lines:
                records_block = "\n".join(checkin_lines)
            else:
                records_block = "（用户尚未添加文案，仅有地点打卡）"

            prompt = (
                f"你是一个旅行故事记录师。以下是一位旅行者在「拾光坐标」平台的打卡数据，"
                f"请根据这些信息生成一份温暖而有个性的「专属足迹报告」。\n\n"
                f"报告要求：\n"
                f"- 用温暖、诗意且有个人感的语言写成，像朋友在回顾旅途\n"
                f"- 总结走过的城市足迹，挖掘旅行风格或偏好\n"
                f"- 篇幅约250-350字，可适当分段，禁止加markdown标题符号(#)\n"
                f"- 结尾送上一句鼓励继续探索的话\n\n"
                f"打卡统计：共 {total} 条记录，走过 {city_count} 座城市：{cities_str}\n\n"
                f"部分打卡内容：\n{records_block}"
            )

            # Call Doubao AI
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    DOUBAO_API_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": endpoint_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 700,
                    },
                )

            if resp.status_code != 200:
                logger.warning("Footprint report failed for user %s: HTTP %s", user_id, resp.status_code)
                _GENERATING.discard(user_id)
                return

            data = resp.json()
            report_text = data["choices"][0]["message"]["content"].strip()
            if not report_text:
                _GENERATING.discard(user_id)
                return

            # Upsert into footprint_reports
            async with async_session_maker() as db2:
                existing = await db2.get(FootprintReport, user_id)
                if existing:
                    existing.content = report_text
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    db2.add(FootprintReport(
                        user_id=user_id,
                        content=report_text,
                        updated_at=datetime.now(timezone.utc),
                    ))
                await db2.commit()

            logger.info("Footprint report generated for user %s", user_id)

    except Exception as exc:
        logger.warning("Footprint report error for user %s: %s", user_id, exc)
    finally:
        _GENERATING.discard(user_id)


def ensure_footprint_report(user_id: int) -> None:
    """Fire-and-forget: schedule report generation if not already in progress."""
    if user_id in _GENERATING:
        return
    if not settings.DOUBAO_API_KEY or not settings.DOUBAO_ENDPOINT_ID:
        return
    _GENERATING.add(user_id)
    asyncio.create_task(_generate_report(user_id))


async def get_footprint_report(user_id: int) -> Optional[str]:
    """Return the cached report text, or None if not yet generated."""
    async with async_session_maker() as db:
        row = await db.get(FootprintReport, user_id)
        return row.content if row else None
