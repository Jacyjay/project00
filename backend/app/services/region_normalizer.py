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


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_region_text(value: Optional[str]) -> Optional[str]:
    cleaned = _normalize_text(value)
    if not cleaned:
        return None

    cleaned = cleaned.replace("臺", "台")

    if cleaned in _TW_VARIANTS:
        return "中国台湾"

    if re.match(r"^(中国)?台(湾|灣)(省)?", cleaned):
        suffix = re.sub(r"^(中国)?台(湾|灣)(省)?", "", cleaned, count=1).strip()
        return f"中国台湾{suffix}" if suffix else "中国台湾"

    if re.match(r"^(中华民国|中華民國)", cleaned):
        suffix = re.sub(r"^(中华民国|中華民國)", "", cleaned, count=1).strip(" ,，")
        return f"中国台湾{suffix}" if suffix else "中国台湾"

    cleaned = re.sub(r"\bTaiwan(?:,?\s*China)?\b", "中国台湾", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bRepublic of China\b", "中国台湾", cleaned, flags=re.IGNORECASE)

    return cleaned


def normalize_city_name(value: Optional[str]) -> Optional[str]:
    normalized = normalize_region_text(value)
    if not normalized:
        return None
    if "中国台湾" in normalized:
        return "中国台湾"
    return normalized

