"""Gmail SMTP multipart email sender (digest + trade alerts)."""

from __future__ import annotations

import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from config import (
    DIGEST_TO,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    TRADE_ALERT_ENABLED,
)

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

    logger.info("Email sent to %s (%s)", recipient, subject)
    return {"ok": True, "to": recipient, "from": sender, "subject": subject}


def send_trade_alert(
    trade: dict[str, Any],
    *,
    equity: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Email a short alert for one filled paper trade. Never raises to callers."""
    if not TRADE_ALERT_ENABLED:
        return None
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("Trade alert skipped: SMTP credentials not configured")
        return None

    side = str(trade.get("type") or "").upper()
    ticker = str(trade.get("ticker") or "")
    shares = trade.get("shares")
    price = trade.get("price")
    source = trade.get("source") or "unknown"
    reasoning = str(trade.get("reasoning") or "").strip()
    realized = trade.get("realized_pnl")
    trade_id = trade.get("id") or ""

    notional = None
    try:
        notional = float(shares) * float(price)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        notional = None

    eq_line = ""
    if equity:
        try:
            eq_line = f"Book equity: ${float(equity.get('equity') or 0):,.2f} | Cash: ${float(equity.get('cash') or 0):,.2f}"
        except (TypeError, ValueError):
            eq_line = ""

    subject = f"[SP500] {side} {shares} {ticker} @ {price}"
    text = "\n".join(
        [
            f"{side} {shares} {ticker} @ ${price}",
            f"Source: {source}",
            f"Trade id: {trade_id}",
            f"Notional: ${notional:,.2f}" if notional is not None else "",
            f"Realized PnL: ${realized}" if realized is not None else "",
            eq_line,
            "",
            "Reasoning:",
            reasoning or "(none)",
        ]
    )
    safe_reason = html.escape(reasoning or "(none)")
    html_body = f"""\
<html><body style="font-family:ui-monospace,monospace;background:#0b0e17;color:#d1d4dc;padding:16px">
  <h2 style="color:#fff;margin:0 0 12px">{html.escape(side)} {html.escape(str(shares))} {html.escape(ticker)}</h2>
  <p style="margin:0 0 8px">Price <strong style="color:#fff">${html.escape(str(price))}</strong>
     · Source <strong>{html.escape(str(source))}</strong>
     · Id <code>{html.escape(str(trade_id))}</code></p>
  {"<p>Notional <strong>$" + f"{notional:,.2f}" + "</strong></p>" if notional is not None else ""}
  {f"<p>Realized PnL <strong>${html.escape(str(realized))}</strong></p>" if realized is not None else ""}
  {f"<p>{html.escape(eq_line)}</p>" if eq_line else ""}
  <h3 style="color:#787b86;font-size:12px;text-transform:uppercase">Reasoning</h3>
  <p style="line-height:1.45">{safe_reason}</p>
</body></html>
"""
    try:
        return send_email(subject=subject, text_body=text, html_body=html_body)
    except Exception:  # noqa: BLE001
        logger.exception("Trade alert email failed for %s %s", side, ticker)
        return {"ok": False, "error": "send failed"}
