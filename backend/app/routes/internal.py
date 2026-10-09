import hmac

from flask import Blueprint, current_app, jsonify, request

from app.utils.errors import ApiError

bp = Blueprint("internal", __name__)


@bp.post("/notifications/process")
def process_notifications():
    """Called by a scheduler (cron). Protected by a shared secret, NOT by a user token."""
    secret = current_app.config["CRON_SECRET"]
    if not secret:
        raise ApiError(404, "not_found", "Not found")          # endpoint disabled when no secret is set
    supplied = request.headers.get("X-Cron-Secret", "")
    if not hmac.compare_digest(supplied.encode(), secret.encode()):   # constant-time comparison
        raise ApiError(401, "unauthorized", "Invalid cron secret")
    return jsonify(current_app.extensions["notifier"].process_due(limit=20))
