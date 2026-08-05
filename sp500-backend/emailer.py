"""Gmail SMTP multipart email sender for the daily digest."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from config import DIGEST_TO, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


def send_email(
    *,
    subject: str,
    text_body: str,
    html_body: str,
    to_addr: str | None = None,
    from_addr: str | None = None,
) -> dict[str, Any]:
    """Send a plain+HTML multipart message via Gmail SMTP (STARTTLS)."""
    recipient = (to_addr or DIGEST_TO or "").strip()
    sender = (from_addr or SMTP_USER or "").strip()
    if not recipient:
        raise RuntimeError("DIGEST_TO is not set")
    if not sender:
        raise RuntimeError("SMTP_USER is not set")
    if not SMTP_PASSWORD:
        raise RuntimeError("SMTP_PASSWORD is not set (use a Gmail App Password)")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=60) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender, SMTP_PASSWORD)
        server.sendmail(sender, [recipient], msg.as_string())

    logger.info("Digest email sent to %s (%s)", recipient, subject)
    return {"ok": True, "to": recipient, "from": sender, "subject": subject}
