from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.region_normalizer import normalize_city_name, normalize_region_text

logger = logging.getLogger(__name__)
INVALID_CITY_NAMES = {"市辖区", "县", "城区"}
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "project00-checkins/1.0",
}
GLOBAL_REGION_SUFFIXES = ("市", "都", "道", "府", "省", "州", "郡", "區", "区", "自治区", "特别行政区", "大区")
ROADLIKE_SUFFIXES = ("路", "街", "大道", "通り", "Avenue", "Street", "Road", "Drive", "Lane", "Boulevard")


class ReverseGeocodeResult:
    def __init__(self, city: Optional[str] = None, address: Optional[str] = None):
        self.city = city
        self.address = address


class PlaceSearchResult:
    def __init__(
        self,
        *,
        id: str,
        name: str,
        city: Optional[str] = None,
        address: Optional[str] = None,
        latitude: float,
        longitude: float,
    ):
        self.id = id
        self.name = name
        self.city = city
        self.address = address
        self.latitude = latitude
        self.longitude = longitude


def _normalize_text(value):
    if isinstance(value, list):
        value = value[0] if value else ""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_region_text(value):
    cleaned = _normalize_text(value)
    if not cleaned:
        return None
    if "/" in cleaned:
        cleaned = cleaned.split("/", 1)[0].strip()
    return cleaned or None


def _normalize_city_candidate(value):
    cleaned = _normalize_text(value)
    if cleaned in INVALID_CITY_NAMES:
        return None
    return cleaned


def _extract_city_from_formatted_address(address: Optional[str]) -> Optional[str]:
    normalized = _normalize_text(address)
    if not normalized:
        return None

    normalized = normalized.removeprefix("中国")
    province_prefix = re.match(r"^.+?(?:省|自治区|特别行政区|市)", normalized)
    remaining = normalized[len(province_prefix.group(0)):] if province_prefix else normalized
    city_match = re.match(r"^.+?(?:市|州|地区|盟)", remaining)
    if city_match:
        return city_match.group(0).strip()
    return None


def _is_municipality_like_region(value: Optional[str]) -> bool:
    return bool(value and (value.endswith("市") or value.endswith("特别行政区")))


def _pick_global_parent_region(display_parts: List[str], city: Optional[str], country: Optional[str]) -> Optional[str]:
    for part in reversed(display_parts[1:]):
        normalized = _normalize_region_text(part)
        if not normalized or normalized == city or normalized == country:
            continue
        if any(char.isdigit() for char in normalized):
            continue
        if normalized.endswith(ROADLIKE_SUFFIXES):
            continue
        if normalized.endswith(GLOBAL_REGION_SUFFIXES):
            return normalized
    return None


def _resolve_nominatim_city(address_data: Optional[Dict], display_name: Optional[str]) -> Optional[str]:
    address_data = address_data or {}
    display_name = _normalize_text(display_name)
    display_parts = [part.strip() for part in (display_name or "").split(",") if part.strip()]
    country = _normalize_region_text(address_data.get("country"))
    state = _normalize_region_text(address_data.get("state"))
    city = (
        _normalize_region_text(address_data.get("city"))
        or _normalize_region_text(address_data.get("town"))
        or _normalize_region_text(address_data.get("municipality"))
        or _normalize_region_text(address_data.get("county"))
        or _normalize_region_text(address_data.get("state_district"))
        or state
        or country
    )
    if not state:
        state = _pick_global_parent_region(display_parts, city, country)
    if city and state and country not in {"中国", "中华人民共和国"} and city.endswith(("区", "區", "郡", "町", "村")):
        city = state
    return city


def _build_nominatim_result(payload: dict) -> ReverseGeocodeResult:
    address_data = payload.get("address") or {}
    display_name = _normalize_text(payload.get("display_name"))
    city = normalize_city_name(_resolve_nominatim_city(address_data, display_name))
    address = normalize_region_text(display_name)
    return ReverseGeocodeResult(city=city, address=address)


def _build_nominatim_place_search_result(payload: Dict, index: int) -> Optional[PlaceSearchResult]:
    display_name = _normalize_text(payload.get("display_name"))
    if not display_name:
        return None

    try:
        latitude = float(payload.get("lat"))
        longitude = float(payload.get("lon"))
    except (TypeError, ValueError):
        return None

    address_data = payload.get("address") or {}
    city = normalize_city_name(_resolve_nominatim_city(address_data, display_name))
    name = (
        _normalize_region_text(payload.get("name"))
        or _normalize_region_text((display_name.split(",", 1)[0] if display_name else None))
        or "未命名地点"
    )
    item_id = str(payload.get("place_id") or payload.get("osm_id") or f"global-{index}")

    return PlaceSearchResult(
        id=item_id,
        name=name,
        city=city,
        address=normalize_region_text(display_name),
        latitude=latitude,
        longitude=longitude,
    )


async def _reverse_geocode_nominatim(latitude: float, longitude: float) -> ReverseGeocodeResult:
    try:
        async with httpx.AsyncClient(timeout=5.0, headers=NOMINATIM_HEADERS) as client:
            response = await client.get(
                NOMINATIM_REVERSE_URL,
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "jsonv2",
                    "accept-language": "zh-CN",
                    "zoom": 10,
                    "addressdetails": 1,
                },
            )
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.warning("Nominatim reverse geocoding failed: %s", exc)
        return ReverseGeocodeResult()

    return _build_nominatim_result(payload)


async def search_places_globally(query: str, limit: int = 8) -> list[PlaceSearchResult]:
    return []


async def reverse_geocode_coordinates(latitude: float, longitude: float) -> ReverseGeocodeResult:
    amap_key = settings.AMAP_KEY
    if not amap_key:
        logger.warning("Amap key not configured, reverse geocoding unavailable")
        return ReverseGeocodeResult()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://restapi.amap.com/v3/geocode/regeo",
                params={
                    "location": f"{longitude},{latitude}",
                    "key": amap_key,
                    "extensions": "base",
                },
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Reverse geocoding request failed: %s", exc)
        return ReverseGeocodeResult()

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning("Reverse geocoding returned invalid JSON: %s", exc)
        return ReverseGeocodeResult()

    if payload.get("status") != "1":
        logger.warning("Amap geocode failed: %s", payload.get("info", "unknown"))
        return ReverseGeocodeResult()

    regeocode = payload.get("regeocode", {})
    address_component = regeocode.get("addressComponent", {})
    province = _normalize_text(address_component.get("province"))
    city = (
        _normalize_city_candidate(address_component.get("city"))
        or _extract_city_from_formatted_address(regeocode.get("formatted_address"))
        or (province if _is_municipality_like_region(province) else None)
        or province
        or _normalize_text(address_component.get("district"))
        or _normalize_text(address_component.get("township"))
        or _normalize_text(address_component.get("country"))
    )
    address = normalize_region_text(_normalize_text(regeocode.get("formatted_address")))
    return ReverseGeocodeResult(city=normalize_city_name(city), address=address)
