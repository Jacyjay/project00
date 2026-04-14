from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncGenerator, Optional

import httpx

from app.core.config import settings
from app.services.region_normalizer import normalize_city_name, normalize_region_text

logger = logging.getLogger(__name__)

DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
AMAP_REVERSE_URL = "https://restapi.amap.com/v3/geocode/regeo"
AMAP_AROUND_URL = "https://restapi.amap.com/v3/place/around"
DEFAULT_QUERY = "推荐附近适合游玩、散步和拍照打卡的地方"
TRAVEL_KEYWORDS = [
    "风景名胜",
    "公园",
    "博物馆",
    "步行街",
]
AI_TRAVEL_CACHE_TTL_SECONDS = 300
AI_TRAVEL_MAX_CANDIDATES = 5
AI_TRAVEL_MAX_HISTORY_ITEMS = 4
AI_TRAVEL_MAX_TOKENS = 220
_AI_TRAVEL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_AMAP_WEB_KEY_WARNING_EMITTED = False


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _distance_to_text(value: Any) -> str:
    raw = _clean_text(str(value or ""))
    if not raw:
        return ""
    try:
        distance = int(float(raw))
    except ValueError:
        return raw
    if distance >= 1000:
        return f"{distance / 1000:.1f}km"
    return f"{distance}m"


def _extract_json_block(content: str) -> str:
    cleaned = _clean_text(content)
    if not cleaned:
        return "{}"

    # Handle ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if fence_match:
        inner = fence_match.group(1).strip()
        if inner.startswith("{"):
            return inner

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start : end + 1]
    return "{}"


def _extract_summary_text(raw: str) -> str:
    """Extract summary text from raw content even when JSON is malformed (e.g. {"summary"=...)."""
    # Try common patterns: "summary": "..." or "summary" = "..."
    match = re.search(r'"summary"\s*[=:]\s*"([^"]{5,})"', raw)
    if match:
        return match.group(1)
    # Strip JSON-like characters and return cleaned snippet
    stripped = re.sub(r'[{}\[\]"=:]', ' ', raw[:300]).strip()
    return stripped if len(stripped) > 10 else ""


def _prune_ai_travel_cache(now: float) -> None:
    expired_keys = [
        key for key, (expires_at, _) in _AI_TRAVEL_CACHE.items()
        if expires_at <= now
    ]
    for key in expired_keys:
        _AI_TRAVEL_CACHE.pop(key, None)


def _build_ai_travel_cache_key(
    *,
    location_summary: str,
    current_detail_location: str,
    current_poi_name: str,
    current_poi_type: str,
    query: str,
    candidate_pois: list[dict[str, Any]],
) -> str:
    rounded_candidates = [
        {
            "name": item.get("name", ""),
            "latitude": round(float(item.get("latitude", 0)), 3),
            "longitude": round(float(item.get("longitude", 0)), 3),
            "distance_text": item.get("distance_text", ""),
        }
        for item in candidate_pois[:AI_TRAVEL_MAX_CANDIDATES]
    ]
    payload = json.dumps(
        {
            "location_summary": location_summary,
            "current_detail_location": current_detail_location,
            "current_poi_name": current_poi_name,
            "current_poi_type": current_poi_type,
            "query": query,
            "candidate_pois": rounded_candidates,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return payload


async def _reverse_geocode_full(latitude: float, longitude: float) -> dict[str, Any]:
    global _AMAP_WEB_KEY_WARNING_EMITTED

    amap_key = settings.amap_web_key
    if not amap_key:
        return {
            "city": "",
            "address": "",
            "district": "",
            "township": "",
            "current_poi_name": "",
            "current_poi_type": "",
        }

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(
                AMAP_REVERSE_URL,
                params={
                    "location": f"{longitude},{latitude}",
                    "key": amap_key,
                    "extensions": "all",
                    "radius": 1000,
                    "roadlevel": 0,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("AI travel reverse geocode failed: %s", exc)
        return {
            "city": "",
            "address": "",
            "district": "",
            "township": "",
            "current_poi_name": "",
            "current_poi_type": "",
        }

    if payload.get("status") != "1":
        info = payload.get("info") or "unknown"
        if info == "USERKEY_PLAT_NOMATCH":
            if not _AMAP_WEB_KEY_WARNING_EMITTED:
                logger.warning("AI travel reverse geocode key mismatch: configure AMAP_WEB_KEY for backend REST APIs")
                _AMAP_WEB_KEY_WARNING_EMITTED = True
        else:
            logger.warning("AI travel reverse geocode returned error: %s", info)
        return {
            "city": "",
            "address": "",
            "district": "",
            "township": "",
            "current_poi_name": "",
            "current_poi_type": "",
        }

    regeocode = payload.get("regeocode") or {}
    address_component = regeocode.get("addressComponent") or {}
    pois = regeocode.get("pois") or []
    first_poi = pois[0] if pois else {}
    province = _clean_text(address_component.get("province"))
    city = (
        _clean_text(address_component.get("city"))
        or province
        or _clean_text(address_component.get("district"))
        or _clean_text(address_component.get("township"))
    )

    return {
        "city": normalize_city_name(city),
        "address": normalize_region_text(regeocode.get("formatted_address")),
        "district": _clean_text(address_component.get("district")),
        "township": _clean_text(address_component.get("township")),
        "current_poi_name": _clean_text(first_poi.get("name")),
        "current_poi_type": _clean_text(first_poi.get("type")),
    }


async def _search_nearby_candidates(
    latitude: float,
    longitude: float,
    *,
    keywords: list[str],
    radius: int,
    page_size: int = 10,
) -> list[dict[str, Any]]:
    amap_key = settings.amap_web_key
    if not amap_key:
        return []

    async def _fetch_one(client: httpx.AsyncClient, keyword: str) -> dict[str, Any]:
        try:
            resp = await client.get(
                AMAP_AROUND_URL,
                params={
                    "key": amap_key,
                    "location": f"{longitude},{latitude}",
                    "keywords": keyword,
                    "radius": radius,
                    "sortrule": "distance",
                    "offset": page_size,
                    "page": 1,
                    "extensions": "base",
                },
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {}

    try:
        # All keywords are fetched concurrently instead of sequentially
        async with httpx.AsyncClient(timeout=5.0) as client:
            payloads = await asyncio.gather(*(_fetch_one(client, kw) for kw in keywords))
    except Exception as exc:
        logger.warning("AI travel nearby POI search failed: %s", exc)
        return []

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    for payload in payloads:
        if payload.get("status") != "1":
            continue
        for poi in payload.get("pois") or []:
            location = _clean_text(poi.get("location"))
            if "," not in location:
                continue
            try:
                lng_text, lat_text = location.split(",", 1)
                poi_longitude = float(lng_text)
                poi_latitude = float(lat_text)
            except ValueError:
                continue

            name = _clean_text(poi.get("name"))
            if not name:
                continue

            dedupe_key = (
                name,
                round(poi_latitude * 10000),
                round(poi_longitude * 10000),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            results.append(
                {
                    "name": name,
                    "address": normalize_region_text(
                        _clean_text(poi.get("address")) or _clean_text(poi.get("pname"))
                    ),
                    "latitude": poi_latitude,
                    "longitude": poi_longitude,
                    "distance_text": _distance_to_text(poi.get("distance")),
                    "type": _clean_text(poi.get("type")) or "",
                }
            )

    return results


def _normalize_candidate(candidate: dict[str, Any]) -> Optional[dict[str, Any]]:
    name = _clean_text(candidate.get("name"))
    if not name:
        return None

    try:
        latitude = float(candidate.get("latitude"))
        longitude = float(candidate.get("longitude"))
    except (TypeError, ValueError):
        return None

    return {
        "name": name,
        "address": normalize_region_text(candidate.get("address")),
        "latitude": latitude,
        "longitude": longitude,
        "distance_text": _clean_text(candidate.get("distance_text")),
        "type": _clean_text(candidate.get("type")) or "地点",
    }


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()

    for candidate in candidates:
        item = _normalize_candidate(candidate)
        if not item:
            continue
        dedupe_key = (
            item["name"],
            round(item["latitude"] * 10000),
            round(item["longitude"] * 10000),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(item)
    return normalized


async def collect_ai_travel_context(
    *,
    latitude: float,
    longitude: float,
    city: str = "",
    address: str = "",
    current_poi_name: str = "",
    current_poi_type: str = "",
    candidate_pois: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    _empty_reverse: dict[str, Any] = {
        "city": "",
        "address": "",
        "district": "",
        "township": "",
        "current_poi_name": "",
        "current_poi_type": "",
    }

    has_frontend_location_context = bool(
        normalize_city_name(city)
        or normalize_region_text(address)
        or _clean_text(current_poi_name)
        or _clean_text(current_poi_type)
    )
    initial_candidates = _dedupe_candidates(candidate_pois or [])
    needs_geocode = not has_frontend_location_context
    needs_poi_search = len(initial_candidates) < 3

    # Parallelize geocoding and first-round POI search when both are needed
    if needs_geocode and needs_poi_search:
        reverse_data, extra_pois = await asyncio.gather(
            _reverse_geocode_full(latitude, longitude),
            _search_nearby_candidates(latitude, longitude, keywords=TRAVEL_KEYWORDS, radius=2500),
        )
        candidates = _dedupe_candidates(initial_candidates + extra_pois)
    elif needs_geocode:
        reverse_data = await _reverse_geocode_full(latitude, longitude)
        candidates = initial_candidates
    elif needs_poi_search:
        reverse_data = _empty_reverse
        extra_pois = await _search_nearby_candidates(
            latitude, longitude, keywords=TRAVEL_KEYWORDS, radius=2500
        )
        candidates = _dedupe_candidates(initial_candidates + extra_pois)
    else:
        reverse_data = _empty_reverse
        candidates = initial_candidates

    # Additional radius rounds only if still insufficient
    if len(candidates) < 8 and needs_poi_search:
        for radius in (5000, 10000):
            if len(candidates) >= 8:
                break
            extra = await _search_nearby_candidates(
                latitude,
                longitude,
                keywords=TRAVEL_KEYWORDS,
                radius=radius,
            )
            candidates = _dedupe_candidates(candidates + extra)

    resolved_city = normalize_city_name(city) or reverse_data.get("city") or ""
    resolved_address = normalize_region_text(address) or reverse_data.get("address") or ""
    resolved_district = _clean_text(reverse_data.get("district"))
    resolved_township = _clean_text(reverse_data.get("township"))
    resolved_current_poi_name = _clean_text(current_poi_name) or reverse_data.get("current_poi_name") or ""
    resolved_current_poi_type = _clean_text(current_poi_type) or reverse_data.get("current_poi_type") or ""

    if not candidates and resolved_current_poi_name:
        candidates = [
            {
                "name": resolved_current_poi_name,
                "address": resolved_address,
                "latitude": latitude,
                "longitude": longitude,
                "distance_text": "当前位置",
                "type": resolved_current_poi_type or "当前位置",
            }
        ]

    location_summary_parts = [part for part in [resolved_city, resolved_address] if part]
    location_summary = " · ".join(location_summary_parts) or "当前位置附近"
    detail_parts = [
        part
        for part in [
            resolved_city,
            resolved_district,
            resolved_township,
            resolved_address,
            resolved_current_poi_name,
        ]
        if part
    ]
    current_detail_location = " / ".join(detail_parts) or location_summary

    return {
        "city": resolved_city,
        "address": resolved_address,
        "district": resolved_district,
        "township": resolved_township,
        "current_poi_name": resolved_current_poi_name,
        "current_poi_type": resolved_current_poi_type,
        "current_detail_location": current_detail_location,
        "location_summary": location_summary,
        "candidate_pois": candidates[:20],
    }


def _build_ai_messages(
    *,
    location_summary: str,
    current_detail_location: str,
    current_poi_name: str,
    current_poi_type: str,
    query: str,
    candidate_pois: list[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
) -> list[dict[str, str]]:
    candidate_pois = candidate_pois[:AI_TRAVEL_MAX_CANDIDATES]
    poi_lines = []
    for index, poi in enumerate(candidate_pois, start=1):
        poi_lines.append(
            f"{index}. {poi['name']}｜类型：{poi.get('type') or '地点'}｜距离：{poi.get('distance_text') or '未知'}｜地址：{poi.get('address') or '未知'}"
        )

    system_prompt = (
        "你是拾光坐标的本地旅行助手。"
        "输出必须是紧凑 JSON 对象，格式为："
        '{"summary":"<=15字总览","recommendations":[{"name":"候选地点名","reason":"<=20字理由","best_time":"<=5字时段","tips":"<=15字提示"}]}。'
        "从候选列表中挑选最适合的 1 到 2 个地点，reason/tips 必须极简。"
        "禁止虚构非候选列表中的地点。不要输出 Markdown，不要加代码块，不要 JSON 之外的文字。"
    )

    user_prompt = (
        f"用户当前区域：{location_summary}\n"
        f"用户当前详细位置：{current_detail_location or location_summary}\n"
        f"当前详细地点：{current_poi_name or '未识别'}\n"
        f"当前地点类型：{current_poi_type or '未知'}\n"
        f"用户需求：{query or DEFAULT_QUERY}\n\n"
        f"候选地点列表：\n" + "\n".join(poi_lines)
    )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for item in (history or [])[-AI_TRAVEL_MAX_HISTORY_ITEMS:]:
        role = item.get("role")
        content = _clean_text(item.get("content"))
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append({"role": role, "content": content[:240]})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _build_fallback_recommendations(
    candidate_pois: list[dict[str, Any]],
    *,
    current_poi_name: str,
    summary_override: str = "",
) -> dict[str, Any]:
    fallback_candidates = candidate_pois[:3]
    recommendations = []
    for item in fallback_candidates:
        is_current_place = bool(current_poi_name and item["name"] == current_poi_name)
        recommendations.append(
            {
                "name": item["name"],
                "address": item.get("address") or "",
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "distance_text": item.get("distance_text") or "",
                "type": item.get("type") or "地点",
                "reason": "你当前所在位置本身就值得停留，可以先从这里开始探索。" if is_current_place else "距离较近，适合顺路去逛逛并继续打卡。",
                "best_time": "全天",
                "tips": "AI 当前较忙，先为你展示附近更适合继续前往的地点。",
            }
        )

    summary = summary_override or (
        "豆包当前请求较多，我先结合你的位置挑出几处附近适合继续游玩和打卡的地方。"
        if recommendations
        else "当前位置周边暂时没有检索到适合推荐的地点，可以尝试移动地图后再试。"
    )
    return {
        "summary": summary,
        "recommendations": recommendations,
    }


async def generate_ai_travel_recommendations(
    *,
    location_summary: str,
    current_detail_location: str,
    current_poi_name: str,
    current_poi_type: str,
    query: str,
    candidate_pois: list[dict[str, Any]],
    history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    api_key = settings.DOUBAO_API_KEY
    endpoint_id = settings.DOUBAO_ENDPOINT_ID
    if not api_key:
        raise ValueError("AI服务未配置：请在.env中设置DOUBAO_API_KEY")
    if not endpoint_id:
        raise ValueError("AI服务未配置：请在.env中设置DOUBAO_ENDPOINT_ID")
    if not candidate_pois:
        return {
            "summary": "当前位置周边暂时没有检索到适合推荐的地点，可以尝试移动地图后再试。",
            "recommendations": [],
        }

    candidate_pois = candidate_pois[:AI_TRAVEL_MAX_CANDIDATES]
    now = time.time()
    _prune_ai_travel_cache(now)
    cache_key = _build_ai_travel_cache_key(
        location_summary=location_summary,
        current_detail_location=current_detail_location,
        current_poi_name=current_poi_name,
        current_poi_type=current_poi_type,
        query=query,
        candidate_pois=candidate_pois,
    )
    cached = _AI_TRAVEL_CACHE.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]

    messages = _build_ai_messages(
        location_summary=location_summary,
        current_detail_location=current_detail_location,
        current_poi_name=current_poi_name,
        current_poi_type=current_poi_type,
        query=query,
        candidate_pois=candidate_pois,
        history=history,
    )

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                DOUBAO_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": endpoint_id,
                    "messages": messages,
                    "max_tokens": AI_TRAVEL_MAX_TOKENS,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            logger.warning("AI travel rate limited; using fallback recommendations")
            fallback_result = _build_fallback_recommendations(
                candidate_pois,
                current_poi_name=current_poi_name,
            )
            _AI_TRAVEL_CACHE[cache_key] = (now + 60, fallback_result)
            return fallback_result
        logger.warning("AI travel request failed: %s", exc)
        fallback_result = _build_fallback_recommendations(
            candidate_pois,
            current_poi_name=current_poi_name,
            summary_override="豆包暂时没有稳定响应，我先为你保留附近仍然适合继续游玩和打卡的地点。",
        )
        _AI_TRAVEL_CACHE[cache_key] = (now + 60, fallback_result)
        return fallback_result
    except Exception as exc:
        logger.warning("AI travel request failed: %s", exc)
        fallback_result = _build_fallback_recommendations(
            candidate_pois,
            current_poi_name=current_poi_name,
            summary_override="豆包这次响应不稳定，我先为你保留附近仍然适合继续游玩和打卡的地点。",
        )
        _AI_TRAVEL_CACHE[cache_key] = (now + 60, fallback_result)
        return fallback_result

    raw_content = _clean_text(payload["choices"][0]["message"]["content"])

    try:
        parsed = json.loads(_extract_json_block(raw_content))
    except json.JSONDecodeError:
        logger.warning("AI travel returned invalid JSON: %s", raw_content[:500])
        # Try to extract a readable summary even from malformed JSON
        extracted = _extract_summary_text(raw_content)
        fallback_summary = extracted or "豆包这次没有按结构化格式返回，我先为你展示附近适合继续游玩和打卡的地点。"
        fallback_result = _build_fallback_recommendations(
            candidate_pois,
            current_poi_name=current_poi_name,
            summary_override=fallback_summary,
        )
        _AI_TRAVEL_CACHE[cache_key] = (now + 60, fallback_result)
        return fallback_result

    summary = _clean_text(parsed.get("summary")) or "附近有几处值得顺路去逛逛的地方。"
    candidate_map = {item["name"]: item for item in candidate_pois}
    recommendations: list[dict[str, Any]] = []

    for item in parsed.get("recommendations") or []:
        name = _clean_text(item.get("name"))
        if not name or name not in candidate_map:
            continue
        candidate = candidate_map[name]
        recommendations.append(
            {
                "name": candidate["name"],
                "address": candidate.get("address") or "",
                "latitude": candidate["latitude"],
                "longitude": candidate["longitude"],
                "distance_text": candidate.get("distance_text") or "",
                "type": candidate.get("type") or "地点",
                "reason": _clean_text(item.get("reason")) or "适合顺路去看看。",
                "best_time": _clean_text(item.get("best_time")) or "全天",
                "tips": _clean_text(item.get("tips")) or "",
            }
        )

    if not recommendations:
        fallback_result = _build_fallback_recommendations(
            candidate_pois,
            current_poi_name=current_poi_name,
        )
        _AI_TRAVEL_CACHE[cache_key] = (now + 60, fallback_result)
        return fallback_result

    result = {
        "summary": summary,
        "recommendations": recommendations[:2],
    }
    _AI_TRAVEL_CACHE[cache_key] = (now + AI_TRAVEL_CACHE_TTL_SECONDS, result)
    return result


# ---------------------------------------------------------------------------
# Streaming chat for follow-up questions
# ---------------------------------------------------------------------------

def _build_chat_messages_for_stream(
    *,
    location_summary: str,
    history: list[dict[str, str]],
    query: str,
) -> list[dict[str, str]]:
    system_prompt = (
        '你是\u201c拾光坐标\u201d的旅行助手豆包。'
        f'用户当前位置：{location_summary or "未知"}。'
        '请根据用户的追问给出简洁、实用、亲切的旅行建议，直接用中文自然回答，'
        '不要输出JSON，不要用Markdown格式，控制在200字以内。'
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    for item in (history or [])[-6:]:
        role = item.get("role")
        content = _clean_text(item.get("content", ""))
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content[:400]})
    messages.append({"role": "user", "content": _clean_text(query)[:300]})
    return messages


async def stream_ai_chat(
    *,
    location_summary: str,
    history: list[dict[str, str]],
    query: str,
) -> AsyncGenerator[str, None]:
    """Yield text chunks from Doubao for a follow-up travel chat question."""
    api_key = settings.DOUBAO_API_KEY
    endpoint_id = settings.DOUBAO_ENDPOINT_ID

    if not api_key or not endpoint_id:
        yield "AI服务未配置，请联系管理员。"
        return

    messages = _build_chat_messages_for_stream(
        location_summary=location_summary,
        history=history,
        query=query,
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                DOUBAO_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": endpoint_id,
                    "messages": messages,
                    "max_tokens": 500,
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        chunk_data = json.loads(data_str)
                        delta = chunk_data["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except httpx.HTTPStatusError as exc:
        logger.warning("AI chat stream HTTP error: %s", exc)
        yield f"\n\n（豆包响应异常 {exc.response.status_code}，请稍后重试）"
    except Exception as exc:
        logger.warning("AI chat stream failed: %s", exc)
        yield "\n\n（豆包响应中断，请稍后重试）"
