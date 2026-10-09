from datetime import datetime, timedelta, timezone

from app.services.email_service import SendError
from tests.conftest import ALICE, BOB, auth


def make(client, assigned=BOB):
    return client.post("/api/tasks", json={"title": "Report", "description": "Q3", "assigned_to": assigned}, headers=auth(ALICE))


def complete(client, tid, user=BOB):
    return client.patch(f"/api/tasks/{tid}/status", json={"status": "completed"}, headers=auth(user))


def test_assignment_creates_outbox_row_and_marks_sent(client, repo, sender):
    make(client)
    (row,) = repo.outbox.values()
    assert row["event_type"] == "task_assigned" and row["status"] == "sent" and row["attempt_count"] == 1
    assert row["sent_at"] is not None and len(sender.sent) == 1


def test_completion_notifies_creator_once(client, repo, sender):
    tid = make(client).get_json()["task"]["id"]
    first = complete(client, tid).get_json()
    again = complete(client, tid).get_json()            # repeat request
    assert first["notification"]["status"] == "sent" and again["notification"]["status"] == "not_required"
    completions = [r for r in sender.sent if r["event_type"] == "task_completed"]
    assert len(completions) == 1 and completions[0]["recipient_email"] == "alice@example.test"


def test_creator_completing_own_task_sends_nothing(client, sender):
    tid = make(client).get_json()["task"]["id"]
    n = len(sender.sent)
    r = complete(client, tid, user=ALICE).get_json()
    assert r["notification"]["status"] == "not_required" and len(sender.sent) == n


def test_reassign_back_to_same_person_does_not_duplicate(client, repo):
    tid = make(client).get_json()["task"]["id"]
    client.patch(f"/api/tasks/{tid}/assignee", json={"assigned_to": BOB}, headers=auth(ALICE))
    assert len(repo.outbox) == 1


def test_temporary_failure_keeps_row_for_retry(client, repo, sender):
    sender.error = SendError("Gmail temporary error (HTTP 503)", True)
    r = make(client)
    assert r.status_code == 201                                       # task is saved...
    assert r.get_json()["notification"]["status"] == "queued"          # ...but we do NOT claim the email was sent
    (row,) = repo.outbox.values()
    assert row["status"] == "pending" and row["last_error"] and row["next_attempt_at"] > datetime.now(timezone.utc)
    assert sender.sent == []


def test_permanent_failure_recorded_as_failed(client, repo, sender):
    sender.error = SendError("Gmail rejected the message (HTTP 400, e.g. invalid recipient)", False)
    r = make(client)
    assert r.get_json()["notification"]["status"] == "failed"
    (row,) = repo.outbox.values()
    assert row["status"] == "failed" and "HTTP 400" in row["last_error"]


def test_unconfigured_gmail_leaves_row_pending(client, repo, sender):
    sender.configured = False
    r = make(client)
    assert r.get_json()["notification"]["status"] == "queued"
    (row,) = repo.outbox.values()
    assert row["status"] == "pending" and row["attempt_count"] == 0


def _make_due(row, attempts=1):
    row.update(status="pending", attempt_count=attempts, next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=1))


def test_cron_retries_a_due_row_after_provider_recovers(client, repo, sender):
    sender.error = SendError("temporary", True)
    make(client)
    (row,) = repo.outbox.values()
    assert row["status"] == "pending"
    sender.error = None                      # Gmail is back
    _make_due(row)
    r = client.post("/api/internal/notifications/process", headers={"X-Cron-Secret": "s3cret"})
    assert r.get_json()["sent"] == 1 and row["status"] == "sent"


def test_row_is_not_retried_before_its_backoff_time(client, repo, sender):
    sender.error = SendError("temporary", True)
    make(client)
    sender.error = None
    r = client.post("/api/internal/notifications/process", headers={"X-Cron-Secret": "s3cret"})
    assert r.get_json()["claimed"] == 0      # next_attempt_at is still in the future


def test_gives_up_after_max_attempts(client, repo, sender):
    sender.error = SendError("temporary", True)
    make(client)
    (row,) = repo.outbox.values()
    _make_due(row, attempts=4)               # claim will make this attempt number 5
    client.post("/api/internal/notifications/process", headers={"X-Cron-Secret": "s3cret"})
    assert row["status"] == "failed" and "Gave up after 5 attempts" in row["last_error"]


def test_cron_endpoint_protected(client):
    assert client.post("/api/internal/notifications/process").status_code == 401
    assert client.post("/api/internal/notifications/process", headers={"X-Cron-Secret": "wrong"}).status_code == 401
    assert client.post("/api/internal/notifications/process", headers=auth()).status_code == 401   # user token is not enough


def test_cron_endpoint_disabled_without_secret(repo, sender):
    from app import create_app
    from app.config import Config
    from app.middleware.auth import TokenVerifier
    from tests.conftest import URL, StubJwks
    app = create_app(Config(supabase_url=URL, supabase_service_role_key="x"), repo=repo, sender=sender,
                     verifier=TokenVerifier(URL, jwks_client=StubJwks()))
    assert app.test_client().post("/api/internal/notifications/process", headers={"X-Cron-Secret": ""}).status_code == 404
