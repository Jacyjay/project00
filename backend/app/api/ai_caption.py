from __future__ import annotations

import base64
import hashlib
import httpx
import logging
import time
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.services.region_normalizer import normalize_city_name

router = APIRouter()
logger = logging.getLogger(__name__)

DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
AI_IMAGE_MAX_DIMENSION = 384
AI_IMAGE_QUALITY = 38
AI_IMAGE_MAX_MODEL_IMAGES = 1
AI_IMAGE_MAX_DATA_URL_BYTES = 220 * 1024
AI_MAX_CAPTIONS = 2
AI_MAX_TOKENS = 320
AI_POLISH_MAX_TOKENS = 240
AI_CACHE_TTL_SECONDS = 600
_CAPTION_CACHE: Dict[str, Tuple[float, List[str]]] = {}


class CaptionRequest(BaseModel):
    city: str
    location_name: str
    image_urls: Optional[List[str]] = []       # public http URLs (not used in this version)
    image_base64s: Optional[List[str]] = []    # base64 encoded images (data:image/xxx;base64,...)
    style: str = "清新风"
    caption_type: str = "旅行文案"
    mode: str = "generate"
    draft_content: str = ""


class CaptionResponse(BaseModel):
    captions: List[str]


def _prune_caption_cache(now: float) -> None:
    expired_keys = [
        key for key, (expires_at, _) in _CAPTION_CACHE.items()
        if expires_at <= now
    ]
    for key in expired_keys:
        _CAPTION_CACHE.pop(key, None)


def _build_cache_key(
    endpoint_id: str,
    prompt: str,
    optimized_images: list[str],
) -> str:
    digest = hashlib.sha256()
    digest.update(endpoint_id.encode("utf-8"))
    digest.update(prompt.encode("utf-8"))
    for image in optimized_images:
        digest.update(image.encode("utf-8"))
    return digest.hexdigest()

def _optimize_image_data_url(data_url: str) -> Optional[str]:
    if not data_url:
        return None

    if not data_url.startswith("data:"):
        data_url = f"data:image/jpeg;base64,{data_url}"

    try:
        _, encoded = data_url.split(",", 1)
        raw_bytes = base64.b64decode(encoded)
    except (ValueError, base64.binascii.Error) as exc:
        logger.warning("AI image decode failed: %s", exc)
        return None

    try:
        with Image.open(BytesIO(raw_bytes)) as image:
            normalized = ImageOps.exif_transpose(image)
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")

            width, height = normalized.size
            longest_side = max(width, height)
            if longest_side > AI_IMAGE_MAX_DIMENSION:
                scale = AI_IMAGE_MAX_DIMENSION / longest_side
                normalized = normalized.resize(
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    Image.Resampling.LANCZOS,
                )

            buffer = BytesIO()
            normalized.save(buffer, format="JPEG", quality=AI_IMAGE_QUALITY, optimize=True)
            optimized = base64.b64encode(buffer.getvalue()).decode("utf-8")
            optimized_data_url = f"data:image/jpeg;base64,{optimized}"
            if len(optimized_data_url.encode("utf-8")) > AI_IMAGE_MAX_DATA_URL_BYTES:
                logger.warning("AI image skipped because optimized payload is still too large")
                return None
            return optimized_data_url
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("AI image optimization failed: %s", exc)
        return None


@router.post("/ai/generate-caption", response_model=CaptionResponse)
async def generate_caption(
    req: CaptionRequest,
    current_user: User = Depends(get_current_user)
):
    api_key = settings.DOUBAO_API_KEY
    endpoint_id = settings.DOUBAO_ENDPOINT_ID
    if not api_key:
        raise HTTPException(status_code=503, detail="AI服务未配置：请在.env中设置DOUBAO_API_KEY")
    if not endpoint_id:
        raise HTTPException(status_code=503, detail="AI服务未配置：请在.env中设置DOUBAO_ENDPOINT_ID（火山方舟接入点ID）")

    style_desc = {
        "清新风": "语言清新自然，简洁明快，充满阳光感",
        "文艺风": "文艺优美，富有诗意，带有人文情怀",
        "日记风": "像日记一样亲切私密，口语化，有温度",
        "轻社交风": "适合发朋友圈，活泼有趣，带emoji，引发互动"
    }.get(req.style, "自然清新")

    type_desc = "旅行打卡" if req.caption_type == "旅行文案" else "日常生活记录"
    mode = (req.mode or "generate").strip().lower()
    if mode not in {"generate", "polish"}:
        raise HTTPException(status_code=422, detail="AI模式不支持")

    draft_content = (req.draft_content or "").strip()
    if mode == "polish" and not draft_content:
        raise HTTPException(status_code=422, detail="请先输入需要润色的文案")

    optimized_images = []
    if mode == "generate":
        for b64 in req.image_base64s:
            image_url = _optimize_image_data_url(b64)
            if image_url:
                optimized_images.append(image_url)
            if len(optimized_images) >= AI_IMAGE_MAX_MODEL_IMAGES:
                break

    has_images = bool(optimized_images)
    city = normalize_city_name((req.city or "未填写城市").strip())[:24]
    location_name = (req.location_name or "未命名地点").strip()[:36]
    image_hint = "请参考图片氛围，但不要逐项描述画面。" if has_images else "没有图片时只根据地点信息生成。"

    if mode == "polish":
        text_prompt = f"""你是一个擅长润色{type_desc}文案的编辑。
请基于以下信息，把用户已经写好的内容润色成{AI_MAX_CAPTIONS}条不同版本，风格为{req.style}（{style_desc}）。

地点：{city} · {location_name}
文案类型：{req.caption_type}
风格要求：{style_desc}
原始文案：{draft_content}

要求：
- 保留原意，不要改动核心事实
- 优化语气、节奏和表达，不要写得太像广告
- 每条文案24-70字
- 两条版本要有细微差异
- 只输出{AI_MAX_CAPTIONS}条
- 每条文案之间用 ||| 分隔
- 不要编号，不要加解释说明"""
    else:
        text_prompt = f"""你是一个擅长写{type_desc}文案的创作者。
请基于以下信息，生成{AI_MAX_CAPTIONS}条不同的{req.caption_type}，风格为{req.style}（{style_desc}）。

地点：{city} · {location_name}
文案类型：{req.caption_type}
风格要求：{style_desc}
补充要求：{image_hint}

要求：
- 每条文案24-60字
- 每条风格略有差异
- 不要编号，直接输出文案内容
- 只输出{AI_MAX_CAPTIONS}条
- 每条文案之间用 ||| 分隔
- 不要加任何解释说明"""
    now = time.time()
    _prune_caption_cache(now)
    cache_key = _build_cache_key(endpoint_id, text_prompt, optimized_images)
    cached_result = _CAPTION_CACHE.get(cache_key)
    if cached_result and cached_result[0] > now:
        return CaptionResponse(captions=cached_result[1])

    if has_images:
        model = endpoint_id
        content = [{"type": "text", "text": text_prompt}]
        for image_url in optimized_images:
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
        messages = [{"role": "user", "content": content}]
    else:
        model = endpoint_id
        messages = [{"role": "user", "content": text_prompt}]

    try:
        async with httpx.AsyncClient(timeout=60.0, http2=False) as client:
            resp = await client.post(
                DOUBAO_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": AI_POLISH_MAX_TOKENS if mode == "polish" else AI_MAX_TOKENS,
                }
            )
            if resp.status_code != 200:
                err_text = resp.text[:300]
                raise HTTPException(status_code=502, detail=f"AI服务错误({resp.status_code}): {err_text}")

            data = resp.json()
            raw = data["choices"][0]["message"]["content"].strip()

            # Parse captions split by |||
            captions = [c.strip() for c in raw.split("|||") if c.strip()]

            # Fallback: split by newline
            if len(captions) <= 1:
                captions = [c.strip() for c in raw.split("\n") if c.strip() and len(c.strip()) > 10][:AI_MAX_CAPTIONS]

            if not captions:
                captions = [raw[:150]] if raw else ["文案生成失败，请重试"]

            final_captions = captions[:AI_MAX_CAPTIONS]
            _CAPTION_CACHE[cache_key] = (now + AI_CACHE_TTL_SECONDS, final_captions)
            return CaptionResponse(captions=final_captions)

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI服务响应超时，请稍后重试")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"AI服务网络异常: {repr(e)[:120]}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务异常: {repr(e)[:120]}")
