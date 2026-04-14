from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
import httpx
import json

from app.core.config import settings

router = APIRouter()

AMAP_STATIC_MAP_URL = "https://restapi.amap.com/v3/staticmap"


@router.get("/api/proxy/amap-static")
async def proxy_amap_static(
    size: str = Query(..., pattern=r"^\d+\*\d+$"),
    location: Optional[str] = Query(default=None),
    markers: Optional[str] = Query(default=None),
    paths: Optional[str] = Query(default=None),
    zoom: str = Query(default="auto"),
):
    """Proxy Gaode static map image to bypass browser CORS restrictions."""
    amap_web_key = settings.amap_web_key
    if not amap_web_key:
        raise HTTPException(status_code=503, detail="AMAP_WEB_KEY not configured")
    if not location and not markers and not paths:
        raise HTTPException(status_code=422, detail="location, markers, or paths is required")

    try:
        params = {
            "size": size,
            "zoom": zoom,
            "scale": 2,
            "key": amap_web_key,
        }
        if location:
            params["location"] = location
        if markers:
            params["markers"] = markers
        if paths:
            params["paths"] = paths

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                AMAP_STATIC_MAP_URL,
                params=params,
            )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type.lower():
            detail = resp.text[:200]
            try:
                payload = resp.json()
                detail = payload.get("info") or payload.get("infocode") or detail
            except (ValueError, json.JSONDecodeError):
                pass
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch static map: {detail}",
            )

        return Response(
            content=resp.content,
            media_type=content_type or "image/png",
            headers={"Cache-Control": "no-store"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch map image: {exc!s}")
