from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.user import User
from app.services.ai_travel import (
    DEFAULT_QUERY,
    collect_ai_travel_context,
    generate_ai_travel_recommendations,
    stream_ai_chat,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai-travel", tags=["ai-travel"])


class AiTravelCandidate(BaseModel):
    name: str
    address: str = ""
    latitude: float
    longitude: float
    distance_text: str = ""
    type: str = ""


class AiTravelHistoryItem(BaseModel):
    role: str
    content: str


class AiTravelRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    city: str = ""
    address: str = ""
    current_poi_name: str = ""
    current_poi_type: str = ""
    query: str = DEFAULT_QUERY
    candidate_pois: Optional[List[AiTravelCandidate]] = []
    history: Optional[List[AiTravelHistoryItem]] = []


class AiTravelRecommendation(AiTravelCandidate):
    reason: str
    best_time: str = ""
    tips: str = ""


class AiTravelResponse(BaseModel):
    location_summary: str
    current_detail_location: str = ""
    current_poi_name: str = ""
    current_poi_type: str = ""
    summary: str
    candidate_pois: List[AiTravelCandidate]
    recommendations: List[AiTravelRecommendation]


class AiTravelChatRequest(BaseModel):
    location_summary: str = ""
    query: str
    history: Optional[List[AiTravelHistoryItem]] = []


@router.post("/recommend", response_model=AiTravelResponse)
async def recommend_ai_travel(
    payload: AiTravelRequest,
    current_user: User = Depends(get_current_user),
):
    del current_user

    context = await collect_ai_travel_context(
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=payload.city,
        address=payload.address,
        current_poi_name=payload.current_poi_name,
        current_poi_type=payload.current_poi_type,
        candidate_pois=[item.model_dump() for item in payload.candidate_pois or []],
    )

    try:
        ai_result = await generate_ai_travel_recommendations(
            location_summary=context["location_summary"],
            current_detail_location=context["current_detail_location"],
            current_poi_name=context["current_poi_name"],
            current_poi_type=context["current_poi_type"],
            query=payload.query,
            candidate_pois=context["candidate_pois"],
            history=[item.model_dump() for item in payload.history or []],
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AiTravelResponse(
        location_summary=context["location_summary"],
        current_detail_location=context["current_detail_location"],
        current_poi_name=context["current_poi_name"],
        current_poi_type=context["current_poi_type"],
        summary=ai_result["summary"],
        candidate_pois=context["candidate_pois"],
        recommendations=ai_result["recommendations"],
    )


@router.post("/chat")
async def chat_ai_travel(
    payload: AiTravelChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Streaming SSE endpoint for follow-up travel chat questions."""
    del current_user

    async def event_generator():
        try:
            async for chunk in stream_ai_chat(
                location_summary=payload.location_summary,
                history=[item.model_dump() for item in payload.history or []],
                query=payload.query,
            ):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.warning("AI chat SSE generator error: %s", exc)
            yield f"data: {json.dumps({'error': '响应出错，请重试'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
