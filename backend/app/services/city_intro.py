from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional, Set

import httpx

from app.core.config import settings
from app.services.region_normalizer import normalize_city_name

logger = logging.getLogger(__name__)

DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# city name → intro text (no TTL: intros don't expire)
_CITY_INTRO_CACHE: Dict[str, str] = {}
# cities currently being generated, to prevent duplicate concurrent requests
_GENERATING: Set[str] = set()


async def _generate_intro(city: str) -> None:
    """Coroutine that calls Doubao and stores the result in cache."""
    api_key = settings.DOUBAO_API_KEY
    endpoint_id = settings.DOUBAO_ENDPOINT_ID
    if not api_key or not endpoint_id:
        _GENERATING.discard(city)
        return

    prompt = (
        f'请用50-80字为旅行平台写一段「{city}」的城市旅行氛围介绍。'
        '要求：语气温暖自然，描述这座城市的整体氛围和旅行感受，'
        '不要像广告，不要说"欢迎来到"之类的套话，直接从城市特质写起。'
        '只输出介绍文字，不要任何说明或标题。'
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                DOUBAO_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": endpoint_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                },
            )
        if resp.status_code != 200:
            logger.warning("City intro failed for %s: HTTP %s", city, resp.status_code)
            return
        data = resp.json()
        intro = data["choices"][0]["message"]["content"].strip()
        if intro:
            _CITY_INTRO_CACHE[city] = intro
            logger.info("City intro cached: %s", city)
    except Exception as exc:
        logger.warning("City intro error for %s: %s", city, exc)
    finally:
        _GENERATING.discard(city)


def ensure_city_intro(city: str) -> None:
    """Fire-and-forget: schedule generation if not cached or already in progress.
    Must be called from within an async context (FastAPI route handler or lifespan).
    """
    city = normalize_city_name(city)
    if not city or city in _CITY_INTRO_CACHE or city in _GENERATING:
        return
    if not settings.DOUBAO_API_KEY or not settings.DOUBAO_ENDPOINT_ID:
        return
    _GENERATING.add(city)
    asyncio.create_task(_generate_intro(city))


def get_city_intro(city: str) -> Optional[str]:
    """Return the cached intro text, or None if not yet generated."""
    return _CITY_INTRO_CACHE.get(normalize_city_name(city))
