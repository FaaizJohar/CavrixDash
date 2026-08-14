from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("email")


def send_email(to: str, subject: str, html: str) -> bool:
    if not settings.smtp_host:
        log.info("email_disabled_skip", to=to, subject=subject)
        return False
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg.set_content("This email requires HTML. Please enable HTML email.")
        msg.add_alternative(html, subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as srv:
            if settings.smtp_tls:
                srv.starttls()
            if settings.smtp_user:
                srv.login(settings.smtp_user, settings.smtp_password)
            srv.send_message(msg)
        log.info("email_sent", to=to, subject=subject)
        return True
    except Exception as exc:  # pragma: no cover
        log.error("email_failed", to=to, subject=subject, error=repr(exc))
        return False


def _base_html(platform: str, content: str) -> str:
    return f"""
    <html><body style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0a0e1a;color:#e2e8f0;padding:24px;">
    <div style="max-width:560px;margin:0 auto;background:#111726;border:1px solid #1e293b;border-radius:12px;padding:28px;">
      <h2 style="margin:0 0 12px;color:#ffffff;">{platform}</h2>
      <div style="line-height:1.6;">{content}</div>
      <p style="margin-top:24px;font-size:12px;color:#64748b;">This is an automated message. Do not reply.</p>
    </div></body></html>"""


def send_verification_email(to: str, link: str, platform: str = "Cavrix Cloud") -> bool:
    return send_email(
        to,
        "Verify your email",
        _base_html(
            platform,
            f"<p>Welcome to {platform}.</p>"
            f'<p><a href="{link}" style="background:#2563eb;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;">Verify email</a></p>'
            f"<p>Or copy: {link}</p>",
        ),
    )


def send_reset_email(to: str, link: str, platform: str = "Cavrix Cloud") -> bool:
    return send_email(
        to,
        "Reset your password",
        _base_html(
            platform,
            f'<p>Reset your password here:</p><p><a href="{link}" style="background:#2563eb;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;">Reset password</a></p>'
            f"<p>Or copy: {link}</p><p>This link expires in 1 hour.</p>",
        ),
    )


def send_notification_email(to: str, subject: str, body_html: str, platform: str = "Cavrix Cloud") -> bool:
    return send_email(to, subject, _base_html(platform, body_html))
