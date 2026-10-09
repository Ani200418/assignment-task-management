import base64
from email import message_from_bytes
from types import SimpleNamespace

import httplib2
import pytest
from google.auth.exceptions import RefreshError, TransportError
from googleapiclient.errors import HttpError

from app.config import Config
from app.services.email_service import GmailSender, SendError, build_message, classify_error

ROW = {"id": "1", "task_id": "t-1", "event_type": "task_assigned", "recipient_email": "bob@example.com",
       "payload": {"task_title": "Fix <b>bug</b>\r\nBcc: evil@example.test", "actor_name": "Alice",
                   "recipient_name": "Bob", "task_description": "Details here"}}


def http_error(status, body=b"{}"):
    return HttpError(httplib2.Response({"status": status}), body)


def test_message_content_and_header_injection_safe():
    m = build_message(ROW, "https://app.example", "sender@example.com")
    assert "\n" not in m["Subject"] and m["Bcc"] is None
    text = m.get_body(("plain",)).get_content()
    assert "https://app.example/tasks/t-1" in text and "Alice" in text
    html = m.get_body(("html",)).get_content()
    assert "<b>bug</b>" not in html and "&lt;b&gt;bug&lt;/b&gt;" in html          # user text is escaped


def test_completion_template():
    row = {**ROW, "event_type": "task_completed", "payload": {"task_title": "T", "actor_name": "Bob", "recipient_name": "Alice", "completed_at": "2026-01-01"}}
    m = build_message(row, "https://app.example", "s@example.com")
    assert m["Subject"] == "Task completed: T" and "Bob marked a task" in m.get_body(("plain",)).get_content()


@pytest.mark.parametrize("exc,retry", [
    (http_error(429), True), (http_error(503), True), (http_error(500), True),
    (http_error(403, b'{"error":{"errors":[{"reason":"rateLimitExceeded"}]}}'), True),
    (http_error(403), False), (http_error(400), False), (http_error(401), False),
    (RefreshError("invalid_grant secret-token-value"), False),
    (TransportError("boom"), True), (TimeoutError(), True), (ValueError("?"), False)])
def test_error_classification(exc, retry):
    err = classify_error(exc)
    assert err.retryable is retry and "secret-token-value" not in str(err)     # provider detail never leaks


class FakeService:
    def __init__(self, error=None):
        self.error, self.body = error, None

    def users(self): return self
    def messages(self): return self

    def send(self, userId, body):
        self.body = body
        return SimpleNamespace(execute=self._exec)

    def _exec(self):
        if self.error:
            raise self.error
        return {"id": "gm-123"}


def sender(service):
    return GmailSender(Config(frontend_url="https://app.example", gmail_sender_email="sender@example.com"), service=service)


def test_send_success_returns_gmail_id_and_valid_raw_message():
    svc = FakeService()
    assert sender(svc).send_row(ROW) == "gm-123"
    raw = message_from_bytes(base64.urlsafe_b64decode(svc.body["raw"]))
    assert raw["To"] == "bob@example.com" and raw["From"] == "sender@example.com"


def test_send_failure_becomes_send_error():
    with pytest.raises(SendError) as e:
        sender(FakeService(http_error(503))).send_row(ROW)
    assert e.value.retryable


def test_invalid_recipient_not_retryable_and_never_calls_gmail():
    svc = FakeService()
    with pytest.raises(SendError) as e:
        sender(svc).send_row({**ROW, "recipient_email": "not-an-email"})
    assert not e.value.retryable and svc.body is None


def test_configured_flag():
    assert not GmailSender(Config()).configured
    assert GmailSender(Config(gmail_client_id="a", gmail_client_secret="b", gmail_refresh_token="c", gmail_sender_email="d")).configured
