from flask import Blueprint, current_app, g, jsonify, request
from pydantic import ValidationError

from app.middleware.auth import require_auth
from app.schemas.tasks import AssigneeUpdate, StatusUpdate, TaskCreate, TaskListQuery, TaskUpdate
from app.utils.errors import ApiError

bp = Blueprint("tasks", __name__)


def _service():
    return current_app.extensions["task_service"]


def _body(model):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Request body must be a JSON object")
    return _validate(model, data)


def _validate(model, data):
    try:
        return model.model_validate(data)
    except ValidationError as e:
        details = [{"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]} for err in e.errors()]
        raise ApiError(422, "validation_error", "Invalid request data", details) from None


@bp.get("")
@require_auth
def list_tasks():
    return jsonify(_service().list(g.user.id, _validate(TaskListQuery, request.args.to_dict())))


@bp.get("/summary")
@require_auth
def summary():
    return jsonify(_service().summary(g.user.id))


@bp.post("")
@require_auth
def create_task():
    return jsonify(_service().create(g.user.id, _body(TaskCreate))), 201


@bp.get("/<task_id>")
@require_auth
def get_task(task_id):
    return jsonify(_service().get(g.user.id, task_id))


@bp.patch("/<task_id>")
@require_auth
def update_task(task_id):
    return jsonify(_service().update_details(g.user.id, task_id, _body(TaskUpdate)))


@bp.patch("/<task_id>/status")
@require_auth
def update_status(task_id):
    return jsonify(_service().set_status(g.user.id, task_id, _body(StatusUpdate)))


@bp.patch("/<task_id>/assignee")
@require_auth
def update_assignee(task_id):
    return jsonify(_service().reassign(g.user.id, task_id, _body(AssigneeUpdate)))


@bp.delete("/<task_id>")
@require_auth
def delete_task(task_id):
    _service().delete(g.user.id, task_id)
    return "", 204
