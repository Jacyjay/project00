import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.security import create_access_token
from app.crud.user import create_user, authenticate_user, get_user_by_email
from app.schemas.user import UserCreate, UserLogin, CurrentUserOut, Token
from app.models.user import User
from app.services.email import send_verification_email
from app.services.verification import save_code, verify_code

router = APIRouter(prefix="/api/auth", tags=["auth"])
LOCAL_DEV_ORIGINS = ("http://127.0.0.1", "http://localhost")
SEND_CODE_TIMEOUT_SECONDS = 25


class SendCodeRequest(BaseModel):
    email: str


class RegisterWithCodeRequest(BaseModel):
    email: str
    code: str
    nickname: str
    password: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


@router.post("/send-code", status_code=200)
async def send_verification_code(
    data: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a 6-digit verification code to the given email for registration."""
    if not data.email or "@" not in data.email:
        raise HTTPException(status_code=422, detail="请输入有效的邮箱地址")

    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    code = save_code(data.email)
    if settings.MAIL_DEBUG_FALLBACK:
        return {
            "message": "邮件服务已切换为调试模式，请使用返回的验证码完成注册",
            "delivery": "debug",
            "dev_code": code,
        }

    try:
        ok = await asyncio.wait_for(
            send_verification_email(data.email, code, purpose="register"),
            timeout=SEND_CODE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        ok = False

    if not ok:
        local_dev_mode = any(origin in settings.BACKEND_CORS_ORIGINS for origin in LOCAL_DEV_ORIGINS)
        if local_dev_mode or settings.MAIL_DEBUG_FALLBACK:
            return {
                "message": "邮件服务暂不可用，已切换为本地调试验证码",
                "delivery": "debug",
                "dev_code": code,
            }
        raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")

    return {"message": "验证码已发送，请查收邮件"}


@router.post("/send-reset-code", status_code=200)
async def send_reset_code(
    data: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a 6-digit verification code to the given email for password reset."""
    if not data.email or "@" not in data.email:
        raise HTTPException(status_code=422, detail="请输入有效的邮箱地址")

    existing = await get_user_by_email(db, data.email)
    if not existing:
        raise HTTPException(status_code=404, detail="该邮箱未注册")

    code = save_code(data.email)
    if settings.MAIL_DEBUG_FALLBACK:
        return {
            "message": "邮件服务已切换为调试模式，请使用返回的验证码重置密码",
            "delivery": "debug",
            "dev_code": code,
        }

    try:
        ok = await asyncio.wait_for(
            send_verification_email(data.email, code, purpose="reset_password"),
            timeout=SEND_CODE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        ok = False

    if not ok:
        local_dev_mode = any(origin in settings.BACKEND_CORS_ORIGINS for origin in LOCAL_DEV_ORIGINS)
        if local_dev_mode or settings.MAIL_DEBUG_FALLBACK:
            return {
                "message": "邮件服务暂不可用，已切换为本地调试验证码",
                "delivery": "debug",
                "dev_code": code,
            }
        raise HTTPException(status_code=500, detail="验证码发送失败，请稍后重试")

    return {"message": "验证码已发送，请查收邮件"}


@router.post("/register", response_model=Token)
async def register(data: RegisterWithCodeRequest, db: AsyncSession = Depends(get_db)):
    """Register with email verification code."""
    if not data.nickname.strip():
        raise HTTPException(status_code=422, detail="昵称不能为空")
    if len(data.password) < 6:
        raise HTTPException(status_code=422, detail="密码至少需要 6 个字符")

    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    if not verify_code(data.email, data.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期，请重新发送")

    user = await create_user(db, data.nickname.strip(), data.email, data.password)
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=access_token,
        user=CurrentUserOut.model_validate(user),
    )


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(
        access_token=access_token,
        user=CurrentUserOut.model_validate(user),
    )


@router.post("/reset-password", status_code=200)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password with email verification code."""
    if not data.email or "@" not in data.email:
        raise HTTPException(status_code=422, detail="请输入有效的邮箱地址")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=422, detail="密码至少需要 6 个字符")

    user = await get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="该邮箱未注册")

    if not verify_code(data.email, data.code):
        raise HTTPException(status_code=400, detail="验证码错误或已过期，请重新发送")

    from app.core.security import get_password_hash
    user.hashed_password = get_password_hash(data.new_password)
    db.add(user)
    await db.commit()

    return {"message": "密码重置成功，请使用新密码登录"}


@router.get("/me", response_model=CurrentUserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return CurrentUserOut.model_validate(current_user)
