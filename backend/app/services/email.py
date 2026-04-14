"""网易163 Mail SMTP email service."""
import asyncio
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)
SMTP_ATTEMPT_TIMEOUT_SECONDS = 8


async def send_verification_email(to_email: str, code: str, purpose: str = "register") -> bool:
    """Send a verification code email via 网易163 Mail SMTP.

    Args:
        to_email: Recipient email address
        code: Verification code
        purpose: "register" or "reset_password"
    """
    if not settings.mail_enabled:
        # In dev mode without mail configured, print the code to console
        print(f"[DEV EMAIL] {purpose} verification code for {to_email}: {code}")
        return True

    def _send():
        context = ssl.create_default_context()
        msg = MIMEMultipart("alternative")

        if purpose == "reset_password":
            msg["Subject"] = "拾光坐标 - 重置密码验证码"
            subtitle = "你正在重置密码，请使用以下验证码完成操作"
            footer = "如果你没有请求重置密码，请忽略此邮件。"
        else:
            msg["Subject"] = "拾光坐标 - 邮箱验证码"
            subtitle = "欢迎加入拾光坐标，一个旅行记录，生活分享社区"
            footer = "如果你没有注册拾光坐标账号，请忽略此邮件。"

        msg["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME
        msg["To"] = to_email

        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 32px 24px; background: #f5f5f7; border-radius: 16px;">
          <h2 style="color: #1d1d1f; font-size: 22px; font-weight: 700; margin-bottom: 8px;">拾光坐标</h2>
          <p style="color: #86868b; font-size: 14px; margin-bottom: 24px;">{subtitle}</p>
          <div style="background: white; border-radius: 12px; padding: 24px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06);">
            <p style="color: #86868b; font-size: 14px; margin-bottom: 12px;">你的验证码是</p>
            <div style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #007AFF; margin: 8px 0;">{code}</div>
            <p style="color: #aeaeb2; font-size: 12px; margin-top: 16px;">验证码 10 分钟内有效，请勿泄露给他人。</p>
          </div>
          <p style="color: #aeaeb2; font-size: 12px; margin-top: 24px; text-align: center;">
            {footer}
          </p>
        </div>
        """
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        sender = settings.MAIL_FROM or settings.MAIL_USERNAME
        attempts = [(settings.MAIL_SSL, settings.MAIL_PORT)]

        if settings.MAIL_SERVER == "smtp.163.com":
            fallbacks = [(True, 465), (True, 994)]
            for fallback in fallbacks:
                if fallback not in attempts:
                    attempts.append(fallback)

        last_error = None
        for use_ssl, port in attempts:
            try:
                logger.info(
                    "Sending verification email via %s:%s ssl=%s to %s",
                    settings.MAIL_SERVER,
                    port,
                    use_ssl,
                    to_email,
                )
                if use_ssl:
                    with smtplib.SMTP_SSL(
                        settings.MAIL_SERVER,
                        port,
                        context=context,
                        timeout=SMTP_ATTEMPT_TIMEOUT_SECONDS,
                    ) as server:
                        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                        server.sendmail(sender, to_email, msg.as_string())
                else:
                    with smtplib.SMTP(
                        settings.MAIL_SERVER,
                        port,
                        timeout=SMTP_ATTEMPT_TIMEOUT_SECONDS,
                    ) as server:
                        server.ehlo()
                        server.starttls(context=context)
                        server.ehlo()
                        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                        server.sendmail(sender, to_email, msg.as_string())
                return True
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Verification email attempt failed via %s:%s ssl=%s to %s: %r",
                    settings.MAIL_SERVER,
                    port,
                    use_ssl,
                    to_email,
                    exc,
                )

        if last_error is not None:
            raise last_error
        return True

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _send)
        return True
    except Exception:
        logger.exception("Failed to send verification email to %s", to_email)
        return False
