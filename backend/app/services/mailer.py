"""Points email over SMTP (Python standard library). Runs after the response is sent; failures are only logged."""
import logging
import re
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger(__name__)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def email_status(address: str) -> str:
    """What will happen to the email: 'sending', 'not_configured' (no SMTP settings) or 'no_address'."""
    if not _EMAIL.match(address or ""):
        return "no_address"  # e.g. a demo-login name that is not an email address
    s = get_settings()
    return "sending" if s.smtp_host and s.mail_from else "not_configured"


def points_summary(points: dict, total_text: str, road: str, upload_id: int) -> str:
    # no photo and no exact location in the email, only what the reporter needs
    return (f"Thank you for reporting a pothole.\n\n"
            f"Points earned: {points['earned']} ({points['reason']})\n"
            f"Your total: {total_text}\n"
            f"Road: {road}\n"
            f"Report ID: {upload_id}\n\n"
            f"SRPPS - Smart Road Pothole Prioritization System\n")


def send(to: str, subject: str, body: str) -> None:
    s = get_settings()
    try:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = s.mail_from, to, subject
        msg.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_pass)
            smtp.send_message(msg)
        log.info("points email sent to %s", to)
    except Exception:
        log.exception("points email to %s failed", to)
