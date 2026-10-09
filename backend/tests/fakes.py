"""In-memory stand-ins for Supabase and Gmail. The fake repository mirrors the SQL functions' rules
(those rules are verified on real PostgreSQL by scripts/test_migrations.py)."""
import uuid
from datetime import datetime, timezone

from app.services.email_service import SendError


def _now():
    return datetime.now(timezone.utc)


class FakeRepo:
    def __init__(self):
        self.profiles, self.tasks, self.outbox = {}, {}, {}

    def add_user(self, uid, email, name=None):
        self.profiles[uid] = {"id": uid, "email": email, "full_name": name, "avatar_url": None}

    # profiles
    def ensure_profile(self, uid, email, name, avatar):
        self.profiles.setdefault(uid, {"id": uid, "email": email, "full_name": name, "avatar_url": avatar})
        return self.profiles[uid]

    def profile_exists(self, uid):
        return uid in self.profiles

    def list_profiles(self, limit=200):
        return list(self.profiles.values())

    # tasks
    def _embed(self, t):
        return {**t, "creator": self.profiles.get(t["created_by"]), "assignee": self.profiles.get(t["assigned_to"])}

    def get_task(self, tid):
        return self._embed(self.tasks[tid]) if tid in self.tasks else None

    def list_tasks(self, uid, role, status, page, page_size):
        def mine(t):
            return {"created": t["created_by"] == uid, "assigned": t["assigned_to"] == uid,
                    "all": uid in (t["created_by"], t["assigned_to"])}[role]
        rows = [t for t in self.tasks.values() if mine(t) and (not status or t["status"] == status)]
        rows.sort(key=lambda t: t["created_at"], reverse=True)
        s = (page - 1) * page_size
        return [self._embed(t) for t in rows[s:s + page_size]], len(rows)

    def task_counts(self, uid):
        mine = [t for t in self.tasks.values() if uid in (t["created_by"], t["assigned_to"])]
        return {s: sum(t["status"] == s for t in mine) for s in ("pending", "in_progress", "completed")}

    def update_task_details(self, tid, fields):
        self.tasks[tid].update(fields)
        return self.get_task(tid)

    def delete_task(self, tid):
        self.tasks.pop(tid, None)
        self.outbox = {k: v for k, v in self.outbox.items() if v["task_id"] != tid}

    # atomic functions
    def _enqueue(self, event, task, recipient, key, actor, extra=None):
        if any(o["dedupe_key"] == key for o in self.outbox.values()):
            return None
        oid = str(uuid.uuid4())
        p = {"task_title": task["title"], "task_description": task["description"],
             "actor_name": actor["full_name"] or actor["email"],
             "recipient_name": recipient["full_name"] or recipient["email"], **(extra or {})}
        self.outbox[oid] = {"id": oid, "event_type": event, "task_id": task["id"], "recipient_email": recipient["email"],
                            "payload": p, "dedupe_key": key, "status": "pending", "attempt_count": 0,
                            "next_attempt_at": _now(), "last_error": None, "sent_at": None}
        return oid

    def rpc_create_task(self, creator, title, description, assignee):
        if assignee and assignee not in self.profiles:
            raise RuntimeError("foreign key violation")
        tid = str(uuid.uuid4())
        t = {"id": tid, "title": title, "description": description or "", "status": "pending", "created_by": creator,
             "assigned_to": assignee, "created_at": _now().isoformat(), "updated_at": _now().isoformat(), "completed_at": None}
        self.tasks[tid] = t
        oid = None
        if assignee and assignee != creator:
            oid = self._enqueue("task_assigned", t, self.profiles[assignee], f"task_assigned:{tid}:{assignee}", self.profiles[creator])
        return {"task_id": tid, "outbox_id": oid}

    def rpc_reassign_task(self, tid, assignee):
        t = self.tasks[tid]
        old, t["assigned_to"] = t["assigned_to"], assignee
        oid = None
        if assignee and assignee != t["created_by"] and assignee != old:
            oid = self._enqueue("task_assigned", t, self.profiles[assignee], f"task_assigned:{tid}:{assignee}", self.profiles[t["created_by"]])
        return {"task_id": tid, "outbox_id": oid}

    def rpc_set_task_status(self, tid, status, actor):
        t = self.tasks[tid]
        if t["status"] == status:
            return {"task_id": tid, "outbox_id": None}
        t["status"] = status
        t["completed_at"] = _now().isoformat() if status == "completed" else None
        oid = None
        if status == "completed" and actor != t["created_by"]:
            oid = self._enqueue("task_completed", t, self.profiles[t["created_by"]],
                                f"task_completed:{tid}:{t['completed_at']}", self.profiles[actor],
                                {"completed_at": t["completed_at"]})
        return {"task_id": tid, "outbox_id": oid}

    # outbox
    def claim_notifications(self, ids=None, limit=10):
        out = []
        for o in self.outbox.values():
            if o["status"] == "pending" and o["next_attempt_at"] <= _now() and (ids is None or o["id"] in ids):
                o["status"] = "processing"
                o["attempt_count"] += 1
                out.append(dict(o))
        return out[:limit]

    def get_notification(self, oid):
        return self.outbox.get(oid)

    def mark_notification_sent(self, oid):
        self.outbox[oid].update(status="sent", sent_at=_now(), last_error=None)

    def mark_notification_retry(self, oid, when, err):
        self.outbox[oid].update(status="pending", next_attempt_at=when, last_error=err)

    def mark_notification_failed(self, oid, err):
        self.outbox[oid].update(status="failed", last_error=err)


class FakeSender:
    """Records messages instead of emailing. Set .error to a SendError to simulate failures."""
    def __init__(self, configured=True):
        self.configured, self.sent, self.error = configured, [], None

    def send_row(self, row):
        if self.error:
            raise self.error
        self.sent.append(row)
        return "gmail-id"


__all__ = ["FakeRepo", "FakeSender", "SendError"]
