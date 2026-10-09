"""Processes the outbox: claim rows -> send -> record the outcome.

Delivery is AT-LEAST-ONCE: if the process dies after Gmail accepted a message but before we mark the row
'sent', the row is reclaimed later and could be sent twice. The unique dedupe_key prevents duplicates
being CREATED; it cannot make the send itself exactly-once. This limitation is documented in the README.
"""
import logging
from datetime import datetime, timedelta, timezone

from .email_service import SendError

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 60       # 1 min, 2 min, 4 min, 8 min ... capped at 1 hour
BACKOFF_CAP_SECONDS = 3600


class NotificationService:
    def __init__(self, repo, sender):
        self.repo, self.sender = repo, sender

    def deliver_one(self, outbox_id) -> str:
        """Try to send one row right now. NEVER raises. Returns 'sent' | 'queued' | 'failed'."""
        try:
            self._process(self._claim([outbox_id]))
            row = self.repo.get_notification(outbox_id)
            return {"sent": "sent", "failed": "failed"}.get(row["status"] if row else "", "queued")
        except Exception:
            log.exception("deliver_one crashed for outbox %s", outbox_id)
            return "queued"

    def process_due(self, limit=10) -> dict:
        """Called by the cron endpoint: retry everything that is due."""
        rows = self._claim(None, limit)
        return self._process(rows)

    def _claim(self, ids, limit=10):
        if not self.sender.configured:
            log.warning("Gmail is not configured; notifications stay pending")
            return []
        return self.repo.claim_notifications(ids, limit)

    def _process(self, rows) -> dict:
        summary = {"claimed": len(rows), "sent": 0, "retry": 0, "failed": 0}
        for row in rows:
            try:
                self.sender.send_row(row)
                self.repo.mark_notification_sent(row["id"])
                summary["sent"] += 1
            except SendError as err:
                if err.retryable and row["attempt_count"] < MAX_ATTEMPTS:
                    delay = min(BACKOFF_BASE_SECONDS * 2 ** (row["attempt_count"] - 1), BACKOFF_CAP_SECONDS)
                    self.repo.mark_notification_retry(
                        row["id"], datetime.now(timezone.utc) + timedelta(seconds=delay), str(err))
                    summary["retry"] += 1
                else:
                    reason = str(err) if not err.retryable else f"Gave up after {MAX_ATTEMPTS} attempts: {err}"
                    self.repo.mark_notification_failed(row["id"], reason)
                    summary["failed"] += 1
                log.warning("Email %s not sent (attempt %s): %s", row["id"], row["attempt_count"], err)
        return summary
