from fastapi import APIRouter, Depends
from app.api.auth import get_current_user
from app.models.user import User
from app.services.footprint_report import get_footprint_report, ensure_footprint_report

router = APIRouter(prefix="/api/footprint-report", tags=["footprint-report"])


@router.get("")
async def get_my_footprint_report(current_user: User = Depends(get_current_user)):
    """Return the pre-generated footprint report for the current user."""
    content = await get_footprint_report(current_user.id)
    return {"content": content}


@router.post("/refresh")
async def refresh_my_footprint_report(current_user: User = Depends(get_current_user)):
    """Manually trigger report regeneration (fire-and-forget)."""
    ensure_footprint_report(current_user.id)
    return {"status": "generating"}
