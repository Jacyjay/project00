from __future__ import annotations

import re
from typing import Optional


_TW_VARIANTS = (
    "中国台湾省",
    "中國台灣省",
    "中国台灣省",
    "中國台湾省",
    "台湾省",
    "台灣省",
    "中国台湾",
    "中國台灣",
    "中国台灣",
    "中國台湾",
    "台湾",
    "台灣",
    "中华民国",
    "中華民國",
)

_TW_CITY_VARIANTS = {
    "台北市",
    "新北市",
    "桃园市",
    "桃園市",
    "台中市",
    "台南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "嘉义市",
    "嘉義市",
    "新竹县",
    "新竹縣",
    "苗栗县",
    "苗栗縣",
    "彰化县",
    "彰化縣",
    "彰化市",
    "南投县",
    "南投縣",
    "云林县",
    "雲林縣",
    "嘉义县",
    "嘉義縣",
    "屏东县",
    "屏東縣",
    "宜兰县",
    "宜蘭縣",
    "花莲县",
    "花蓮縣",
    "台东县",
    "台東縣",
    "澎湖县",
    "澎湖縣",
    "金门县",
    "金門縣",
    "连江县",
    "連江縣",
}


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _with_taiwan_prefix(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return "台湾省"
    if cleaned == "台湾省":
        return cleaned
    if cleaned.startswith("台湾省"):
        return cleaned
    if cleaned in _TW_CITY_VARIANTS:
        return f"台湾省{cleaned}"
    return cleaned


def normalize_region_text(value: Optional[str]) -> Optional[str]:
    cleaned = _normalize_text(value)
    if not cleaned:
        return None

    # Convert common Traditional Chinese characters used in Taiwan place names
    cleaned = (
        cleaned
        .replace("臺", "台")
        .replace("灣", "湾")
        .replace("區", "区")
        .replace("縣", "县")
    )

    if cleaned in _TW_VARIANTS:
        return "台湾省"

    if re.match(r"^(中国)?台(湾|灣)(省)?", cleaned):
        suffix = re.sub(r"^(中国)?台(湾|灣)(省)?", "", cleaned, count=1).strip()
        return _with_taiwan_prefix(f"台湾省{suffix}" if suffix else "台湾省")

    if re.match(r"^(中华民国|中華民國)", cleaned):
        suffix = re.sub(r"^(中华民国|中華民國)", "", cleaned, count=1).strip(" ,，")
        return _with_taiwan_prefix(f"台湾省{suffix}" if suffix else "台湾省")

    cleaned = re.sub(r"\bTaiwan(?:,?\s*China)?\b", "台湾省", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bRepublic of China\b", "台湾省", cleaned, flags=re.IGNORECASE)

    # Handle Nominatim-style addresses where 台湾 appears at the end:
    # e.g. "潭子区, 台中市, 台湾" → "台湾省台中市潭子区"
    tw_suffix = re.search(r",?\s*台(湾|灣)(省)?$", cleaned)
    if tw_suffix:
        inner = cleaned[: tw_suffix.start()].strip().strip(",").strip()
        if inner:
            parts = [p.strip() for p in inner.split(",") if p.strip()]
            parts.reverse()  # Nominatim is small→large; reverse to Chinese large→small
            return f"台湾省{''.join(parts)}"
        return "台湾省"

    return _with_taiwan_prefix(cleaned)


def normalize_city_name(value: Optional[str]) -> Optional[str]:
    normalized = normalize_region_text(value)
    if not normalized:
        return None
    return normalized
