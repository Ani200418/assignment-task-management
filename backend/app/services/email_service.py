"""Builds the emails and sends them through the Gmail API.

Gmail is a SEPARATE OAuth purpose from Google sign-in: a dedicated sender account authorises
this server ONCE (scope: gmail.send only) and we keep its refresh token in an environment variable.
"Sent" here means Gmail's API ACCEPTED the message and returned an id. It does not prove inbox delivery.
"""
import base64
import html
import logging
import socket
from email.message import EmailMessage

from pydantic import EmailStr, TypeAdapter, ValidationError

log = logging.getLogger(__name__)
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
_email_adapter = TypeAdapter(EmailStr)


class SendError(Exception):
    """retryable=True -> try again later; False -> give up and record the failure."""
    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


def _clean(text: str) -> str:
    """Single-line, no control characters: stops header injection through a task title."""
    return " ".join(str(text).split())[:200]


def build_message(row: dict, frontend_url: str, sender_email: str) -> EmailMessage:
    p = row.get("payload") or {}
    title, actor = _clean(p.get("task_title", "Task")), _clean(p.get("actor_name", "Someone"))
    name = _clean(p.get("recipient_name", "there"))
    link = f"{frontend_url}/tasks/{row['task_id']}"
    if row["event_type"] == "task_assigned":
        subject = f"New task assigned to you: {title}"
        lines = [f"{actor} assigned you a task.", f"Task: {title}"]
        if p.get("task_description"):
            lines.append(f"Details: {p['task_description'][:500]}")
    else:
        subject = f"Task completed: {title}"
        lines = [f"{actor} marked a task you created as completed.", f"Task: {title}"]
        if p.get("completed_at"):
            lines.append(f"Completed at: {p['completed_at']}")
    text = f"Hi {name},\n\n" + "\n".join(lines) + f"\n\nOpen the task: {link}\n"
    body = "".join(f"<p style='margin:0 0 8px'>{html.escape(l)}</p>" for l in lines)
    page = (f"<div style='font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:16px'>"
            f"<p>Hi {html.escape(name)},</p>{body}"
            f"<p><a href='{html.escape(link)}' style='background:#4f46e5;color:#fff;padding:10px 16px;"
            f"border-radius:6px;text-decoration:none;display:inline-block'>Open task</a></p></div>")
    msg = EmailMessage()
    msg["To"], msg["From"], msg["Subject"] = row["recipient_email"], sender_email, subject
    msg.set_content(text)
    msg.add_alternative(page, subtype="html")
    return msg


def classify_error(exc: Exception) -> SendError:
    """Turn any provider/network exception into a SendError with a SAFE message (no provider body, no tokens)."""
    from google.auth.exceptions import RefreshError, TransportError
    from googleapiclient.errors import HttpError

    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", 0)
        body = str(getattr(exc, "content", b""))
        if status in RETRYABLE_HTTP or (status == 403 and "ateLimit" in body):
            return SendError(f"Gmail temporary error (HTTP {status})", True)
        if status == 400:
            return SendError("Gmail rejected the message (HTTP 400, e.g. invalid recipient)", False)
        return SendError(f"Gmail authorization or request error (HTTP {status})", False)
    if isinstance(exc, RefreshError):
        return SendError("Gmail credentials rejected (refresh token invalid, revoked or expired)", False)
    if isinstance(exc, (TransportError, socket.timeout, TimeoutError, ConnectionError, OSError)):
        return SendError("Network problem talking to Gmail", True)
    return SendError(f"Unexpected email error ({type(exc).__name__})", False)


class GmailSender:
    def __init__(self, config, service=None):
        self.config = config
        self._service = service  # tests inject a fake

    @property
    def configured(self) -> bool:
        return self._service is not None or self.config.gmail_configured

    def _get_service(self):
        if self._service is None:
            import google_auth_httplib2
            import httplib2
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            creds = Credentials(
                token=None, refresh_token=self.config.gmail_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.config.gmail_client_id, client_secret=self.config.gmail_client_secret,
                scopes=GMAIL_SCOPES,
            )
            http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=10))
            self._service = build("gmail", "v1", http=http, cache_discovery=False)
        return self._service

    def send_row(self, row: dict) -> str:
        """Send one outbox row. Returns the Gmail message id or raises SendError."""
        try:
            _email_adapter.validate_python(row["recipient_email"])
        except ValidationError:
            raise SendError("Invalid recipient address", False) from None
        msg = build_message(row, self.config.frontend_url, self.config.gmail_sender_email)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        try:
            res = self._get_service().users().messages().send(userId="me", body={"raw": raw}).execute()
        except Exception as exc:  # noqa: BLE001 - classified below
            raise classify_error(exc) from None
        return res.get("id", "")
