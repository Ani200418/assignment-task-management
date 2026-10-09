"""All database access lives here. Uses the service-role client (bypasses RLS), so the
callers (services) are responsible for authorization before calling these methods."""
from datetime import datetime, timezone

from supabase import create_client

from app.utils.ids import parse_uuid

PROFILE_FIELDS = "id,email,full_name,avatar_url"
TASK_SELECT = (
    "*, creator:profiles!tasks_created_by_fkey(id,email,full_name,avatar_url), "
    "assignee:profiles!tasks_assigned_to_fkey(id,email,full_name,avatar_url)"
)


def _now():
    return datetime.now(timezone.utc).isoformat()


class SupabaseRepository:
    def __init__(self, url: str, service_role_key: str):
        self.db = create_client(url, service_role_key)

    # ---- profiles -------------------------------------------------------
    def ensure_profile(self, user_id, email, full_name, avatar_url) -> dict:
        row = {"id": user_id, "email": email, "full_name": full_name, "avatar_url": avatar_url}
        res = self.db.table("profiles").upsert(row, on_conflict="id").execute()
        return res.data[0]

    def profile_exists(self, user_id) -> bool:
        res = self.db.table("profiles").select("id").eq("id", parse_uuid(user_id)).limit(1).execute()
        return bool(res.data)

    def list_profiles(self, limit=200) -> list:
        return self.db.table("profiles").select(PROFILE_FIELDS).order("full_name").limit(limit).execute().data

    # ---- tasks ----------------------------------------------------------
    def get_task(self, task_id):
        res = self.db.table("tasks").select(TASK_SELECT).eq("id", task_id).limit(1).execute()
        return res.data[0] if res.data else None

    def list_tasks(self, user_id, role, status, page, page_size):
        uid = parse_uuid(user_id)  # validated, so safe to place in the filter string below
        q = self.db.table("tasks").select(TASK_SELECT, count="exact")
        if role == "created":
            q = q.eq("created_by", uid)
        elif role == "assigned":
            q = q.eq("assigned_to", uid)
        else:
            q = q.or_(f"created_by.eq.{uid},assigned_to.eq.{uid}")
        if status:
            q = q.eq("status", status)
        start = (page - 1) * page_size
        res = q.order("created_at", desc=True).range(start, start + page_size - 1).execute()
        return res.data, res.count or 0

    def task_counts(self, user_id) -> dict:
        uid = parse_uuid(user_id)
        counts = {}
        for status in ("pending", "in_progress", "completed"):
            res = (self.db.table("tasks").select("id", count="exact", head=True)
                   .or_(f"created_by.eq.{uid},assigned_to.eq.{uid}").eq("status", status).execute())
            counts[status] = res.count or 0
        return counts

    def update_task_details(self, task_id, fields: dict):
        self.db.table("tasks").update(fields).eq("id", task_id).execute()
        return self.get_task(task_id)

    def delete_task(self, task_id):
        self.db.table("tasks").delete().eq("id", task_id).execute()

    # ---- atomic writes (SQL functions: task change + outbox row in one transaction) ----
    def rpc_create_task(self, creator, title, description, assignee) -> dict:
        return self.db.rpc("create_task", {"p_creator": creator, "p_title": title,
                                           "p_description": description, "p_assignee": assignee}).execute().data

    def rpc_reassign_task(self, task_id, assignee) -> dict:
        return self.db.rpc("reassign_task", {"p_task": task_id, "p_assignee": assignee}).execute().data

    def rpc_set_task_status(self, task_id, status, actor) -> dict:
        return self.db.rpc("set_task_status", {"p_task": task_id, "p_status": status, "p_actor": actor}).execute().data

    # ---- outbox ---------------------------------------------------------
    def claim_notifications(self, ids=None, limit=10) -> list:
        return self.db.rpc("claim_notifications", {"p_ids": ids, "p_limit": limit}).execute().data or []

    def get_notification(self, outbox_id):
        res = self.db.table("notification_outbox").select("*").eq("id", outbox_id).limit(1).execute()
        return res.data[0] if res.data else None

    def mark_notification_sent(self, outbox_id):
        self._update_outbox(outbox_id, {"status": "sent", "sent_at": _now(), "last_error": None, "locked_at": None})

    def mark_notification_retry(self, outbox_id, next_attempt_at: datetime, error: str):
        self._update_outbox(outbox_id, {"status": "pending", "next_attempt_at": next_attempt_at.isoformat(),
                                        "last_error": error, "locked_at": None})

    def mark_notification_failed(self, outbox_id, error: str):
        self._update_outbox(outbox_id, {"status": "failed", "last_error": error, "locked_at": None})

    def _update_outbox(self, outbox_id, fields):
        self.db.table("notification_outbox").update(fields).eq("id", outbox_id).execute()
