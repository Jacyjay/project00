import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, async_session_maker
from app.models import User, Place, Checkin, Photo, Message, FootprintReport, Follow  # noqa: import all models
from app.models.social import Like, Comment  # noqa: import social models for table creation
from app.api.auth import router as auth_router
from app.api.places import router as places_router
from app.api.checkins import router as checkins_router
from app.api.users import router as users_router
from app.api.messages import router as messages_router
from app.api.uploads import router as uploads_router
from app.api import social, ai_caption
from app.api.footprint_report import router as footprint_report_router
from app.api.follows import router as follows_router
from app.services.city_intro import ensure_city_intro

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-generate city intros for all cities that already exist in the database.
    # This ensures existing check-ins have intros available without waiting for
    # a new publish to trigger generation.
    try:
        async with async_session_maker() as db:
            result = await db.execute(
                select(Checkin.city)
                .where(Checkin.city.isnot(None), Checkin.city != "")
                .distinct()
            )
            cities = [row[0] for row in result.all()]
        for city in cities:
            ensure_city_intro(city)
        if cities:
            logger.info("City intro warmup triggered for %d cities", len(cities))
    except Exception as exc:
        logger.warning("City intro warmup failed: %s", exc)
    yield


app = FastAPI(
    title="拾光坐标 API",
    description="基于地图聚合的旅行打卡与分享平台",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount upload directory for serving images
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth_router)
app.include_router(places_router)
app.include_router(checkins_router)
app.include_router(users_router)
app.include_router(messages_router)
app.include_router(uploads_router)
app.include_router(social.router, prefix="/api", tags=["social"])
app.include_router(ai_caption.router, prefix="/api", tags=["ai"])
app.include_router(footprint_report_router)
app.include_router(follows_router)


@app.get("/")
async def root():
    return {"message": "拾光坐标 API 运行中", "docs": "/docs", "version": "2.0.0"}
