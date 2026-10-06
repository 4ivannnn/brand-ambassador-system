"""Notification service (the 'Notification' class / 'Notification service' lifeline).

Every notification is stored in the notifications table (shown on the dashboard).
If SMTP_HOST is set in .env an e-mail is sent as well (proposal: "notifications may be
pushed to marketing teams through email").
"""
import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import Notification, User

log = logging.getLogger(__name__)


def _send_email(to: str, subject: str, body: str) -> None:
    if not config.SMTP_HOST:
        return
    try:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = config.SMTP_FROM, to, subject
        msg.set_content(body)
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            if config.SMTP_USER:
                smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
            smtp.send_message(msg)
    except Exception:                       # never let a mail problem break an approval
        log.exception("Could not send e-mail to %s", to)


def send(db: Session, user: User, request_id: int | None, message: str) -> None:
    db.add(Notification(user_id=user.user_id, request_id=request_id, message=message))
    _send_email(user.email, "Brand ambassador activation update", message)


def notify_supplier(db: Session, supplier_id: int, request_id: int, message: str) -> None:
    for u in db.scalars(select(User).where(User.supplier_id == supplier_id)):
        send(db, u, request_id, message)


def notify_managers(db: Session, request_id: int, message: str) -> None:
    for u in db.scalars(select(User).where(User.role == "APPROVING_MANAGER")):
        send(db, u, request_id, message)


def notify_user(db: Session, user_id: int | None, request_id: int, message: str) -> None:
    if user_id is None:
        return
    user = db.get(User, user_id)
    if user:
        send(db, user, request_id, message)
