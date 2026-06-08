from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def email_enabled() -> bool:
    """Подтверждение email включается, когда заданы SMTP-логин и пароль."""
    return bool(os.getenv("SMTP_USER")) and bool(os.getenv("SMTP_PASSWORD"))


def _base_url() -> str:
    return os.getenv("APP_BASE_URL", "https://construction-budget-agent-v3.onrender.com").rstrip("/")


def send_verification_email(to_email: str, token: str) -> None:
    """Отправляет письмо со ссылкой подтверждения. Бросает исключение при ошибке."""
    host = os.getenv("SMTP_HOST", "smtp.yandex.ru")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM") or user
    link = f"{_base_url()}/api/auth/verify?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Подтверждение регистрации — Construction Budget Agent"
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(
        "Здравствуйте!\n\n"
        "Вы зарегистрировались в сервисе Construction Budget Agent.\n"
        f"Подтвердите адрес, перейдя по ссылке:\n{link}\n\n"
        "Ссылка действует 24 часа. Если вы не регистрировались — игнорируйте это письмо."
    )
    msg.add_alternative(
        f"""<html><body style="font-family:Arial,sans-serif;color:#16213a">
<p>Здравствуйте!</p>
<p>Вы зарегистрировались в сервисе <b>Construction Budget Agent</b>.</p>
<p><a href="{link}" style="background:#2f6df0;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none">Подтвердить email</a></p>
<p>Или скопируйте ссылку:<br>{link}</p>
<p style="color:#5b6b88;font-size:13px">Ссылка действует 24 часа. Если вы не регистрировались — игнорируйте письмо.</p>
</body></html>""",
        subtype="html",
    )

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=20) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, password)
            server.send_message(msg)
