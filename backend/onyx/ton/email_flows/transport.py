"""E-mail transport for TON flows: Resend (HTTP API) or SMTP, chosen by
``TON_EMAIL_PROVIDER``. Without a configured provider nothing is sent and the
delivery is recorded as not configured; previews keep working."""

import base64
import os
import smtplib
from dataclasses import dataclass
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import httpx

from onyx.configs.app_configs import (
    EMAIL_FROM,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_STARTTLS,
    SMTP_USER,
)

RESEND_URL = "https://api.resend.com/emails"
# Resend accepts at most 50 recipients per message (to + cc + bcc).
RESEND_MAX_RECIPIENTS = 50


@dataclass(frozen=True)
class InlineImage:
    """An image the HTML references as ``cid:<content_id>``."""

    content_id: str
    filename: str
    content_type: str
    data: bytes


@dataclass(frozen=True)
class OutgoingEmail:
    to: list[str]
    cc: list[str]
    bcc: list[str]
    subject: str
    html: str
    text: str
    images: tuple[InlineImage, ...] = ()


@dataclass(frozen=True)
class SendResult:
    provider_message_id: str | None


class TransportError(Exception):
    pass


class EmailTransport:
    name: str
    max_recipients: int
    sender: str

    def send(self, message: OutgoingEmail) -> SendResult:
        raise NotImplementedError


class ResendTransport(EmailTransport):
    name = "resend"
    max_recipients = RESEND_MAX_RECIPIENTS

    def __init__(self, api_key: str, sender: str) -> None:
        self._api_key = api_key
        self.sender = sender

    def send(self, message: OutgoingEmail) -> SendResult:
        payload: dict[str, object] = {
            "from": self.sender,
            "to": message.to,
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        if message.cc:
            payload["cc"] = message.cc
        if message.bcc:
            payload["bcc"] = message.bcc
        if message.images:
            # Inline images: Resend matches content_id to cid: in the HTML.
            payload["attachments"] = [
                {
                    "filename": image.filename,
                    "content": base64.b64encode(image.data).decode("ascii"),
                    "content_type": image.content_type,
                    "content_id": image.content_id,
                }
                for image in message.images
            ]
        try:
            response = httpx.post(
                RESEND_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=30,
            )
        except httpx.HTTPError as error:
            raise TransportError(f"Resend indisponível: {type(error).__name__}") from None
        if response.status_code >= 400:
            try:
                detail = str(response.json().get("message") or response.text)
            except ValueError:
                detail = response.text
            raise TransportError(f"Resend recusou o envio ({response.status_code}): {detail[:300]}")
        return SendResult(str(response.json().get("id") or "") or None)


class SmtpTransport(EmailTransport):
    """Same SMTP settings as ``onyx.auth.email_utils``; that helper sends to one
    address, while a flow sends one message to To, Cc and Bcc together."""

    name = "smtp"

    def __init__(self, sender: str, max_recipients: int) -> None:
        self.sender = sender
        self.max_recipients = max_recipients

    def send(self, message: OutgoingEmail) -> SendResult:
        mime = MIMEMultipart("related") if message.images else MIMEMultipart("alternative")
        mime["Subject"] = message.subject
        mime["From"] = self.sender
        mime["To"] = ", ".join(message.to)
        if message.cc:
            mime["Cc"] = ", ".join(message.cc)
        mime["Date"] = formatdate(localtime=True)
        message_id = make_msgid()
        mime["Message-ID"] = message_id
        if message.images:
            body = MIMEMultipart("alternative")
            body.attach(MIMEText(message.text, "plain", "utf-8"))
            body.attach(MIMEText(message.html, "html", "utf-8"))
            mime.attach(body)
            for image in message.images:
                part = MIMEImage(image.data, _subtype=image.content_type.split("/")[-1])
                part.add_header("Content-ID", f"<{image.content_id}>")
                part.add_header("Content-Disposition", "inline", filename=image.filename)
                mime.attach(part)
        else:
            mime.attach(MIMEText(message.text, "plain", "utf-8"))
            mime.attach(MIMEText(message.html, "html", "utf-8"))
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
                if SMTP_STARTTLS:
                    server.starttls()
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(
                    mime, to_addrs=[*message.to, *message.cc, *message.bcc]
                )
        except (smtplib.SMTPException, OSError) as error:
            raise TransportError(f"SMTP falhou: {type(error).__name__}: {error}"[:300]) from None
        return SendResult(message_id)


def _sender() -> str:
    return os.environ.get("TON_EMAIL_FROM") or EMAIL_FROM or ""


def provider_name() -> str | None:
    value = (os.environ.get("TON_EMAIL_PROVIDER") or "").strip().lower()
    return value or None


def get_transport() -> EmailTransport | None:
    """The configured transport, or ``None`` when sending is not set up."""
    provider = provider_name()
    sender = _sender()
    if provider == "resend":
        key = os.environ.get("RESEND_API_KEY") or ""
        return ResendTransport(key, sender) if key and sender else None
    if provider == "smtp":
        limit = int(os.environ.get("TON_EMAIL_MAX_RECIPIENTS") or 50)
        return SmtpTransport(sender, limit) if SMTP_SERVER and sender else None
    return None


def sender_address() -> str | None:
    return _sender() or None
