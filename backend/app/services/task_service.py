"""AUTHORIZATION lives here: who may do what to which task.

Rules (approved):  creator -> view/edit/reassign/status/delete.  assignee -> view + status.
Everyone else gets 404 (we do not reveal that the task exists).
"""
from app.utils.errors import ApiError, not_found
from app.utils.ids import parse_uuid


def permissions_for(task: dict, user_id: str) -> dict:
    creator, assignee = task["created_by"] == user_id, task.get("assigned_to") == user_id
    return {"can_edit": creator, "can_reassign": creator, "can_delete": creator,
            "can_change_status": creator or assignee}


class TaskService:
    def __init__(self, repo, notifier):
        self.repo, self.notifier = repo, notifier

    # ---- helpers ----------------------------------------------------------
    def _visible_task(self, user_id: str, task_id: str) -> dict:
        task = self.repo.get_task(parse_uuid(task_id, "task_id"))
        if task is None or user_id not in (task["created_by"], task.get("assigned_to")):
            raise not_found("Task")          # same answer for "missing" and "not yours"
        return task

    def _present(self, task: dict, user_id: str) -> dict:
        return {**task, "permissions": permissions_for(task, user_id)}

    def _deliver(self, outbox_id) -> dict:
        if outbox_id is None:
            return {"status": "not_required"}
        return {"status": self.notifier.deliver_one(outbox_id)}   # sent | queued | failed

    def _require_creator(self, task, user_id, action):
        if task["created_by"] != user_id:
            raise ApiError(403, "forbidden", f"Only the task creator can {action}")

    # ---- use cases --------------------------------------------------------
    def list(self, user_id, q):
        items, total = self.repo.list_tasks(user_id, q.role, q.status, q.page, q.page_size)
        return {"tasks": [self._present(t, user_id) for t in items], "page": q.page,
                "page_size": q.page_size, "total": total}

    def get(self, user_id, task_id):
        return {"task": self._present(self._visible_task(user_id, task_id), user_id)}

    def create(self, user_id, data):
        assignee = str(data.assigned_to) if data.assigned_to else None
        if assignee and not self.repo.profile_exists(assignee):
            raise ApiError(422, "assignee_not_found", "The selected assignee is not a registered user")
        result = self.repo.rpc_create_task(user_id, data.title, data.description, assignee)
        task = self.repo.get_task(result["task_id"])
        return {"task": self._present(task, user_id), "notification": self._deliver(result.get("outbox_id"))}

    def update_details(self, user_id, task_id, data):
        task = self._visible_task(user_id, task_id)
        self._require_creator(task, user_id, "edit this task")
        fields = data.model_dump(exclude_none=True)
        return {"task": self._present(self.repo.update_task_details(task["id"], fields), user_id)}

    def set_status(self, user_id, task_id, data):
        task = self._visible_task(user_id, task_id)        # creator or assignee only (else 404)
        result = self.repo.rpc_set_task_status(task["id"], data.status, user_id)
        return {"task": self._present(self.repo.get_task(task["id"]), user_id),
                "notification": self._deliver(result.get("outbox_id"))}

    def reassign(self, user_id, task_id, data):
        task = self._visible_task(user_id, task_id)
        self._require_creator(task, user_id, "reassign this task")
        assignee = str(data.assigned_to) if data.assigned_to else None
        if assignee and not self.repo.profile_exists(assignee):
            raise ApiError(422, "assignee_not_found", "The selected assignee is not a registered user")
        result = self.repo.rpc_reassign_task(task["id"], assignee)
        return {"task": self._present(self.repo.get_task(task["id"]), user_id),
                "notification": self._deliver(result.get("outbox_id"))}

    def delete(self, user_id, task_id):
        task = self._visible_task(user_id, task_id)
        self._require_creator(task, user_id, "delete this task")
        self.repo.delete_task(task["id"])

    def summary(self, user_id):
        return {"counts": self.repo.task_counts(user_id)}
