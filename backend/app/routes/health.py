from flask import Blueprint, current_app, g, jsonify

from app.middleware.auth import require_auth

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@bp.get("/me")
@require_auth
def me():
    """Returns the caller's profile, creating it on first call if the DB trigger has not."""
    u = g.user
    profile = current_app.extensions["repo"].ensure_profile(u.id, u.email, u.full_name, u.avatar_url)
    return jsonify({"user": profile})


@bp.get("/users/assignable")
@require_auth
def assignable():
    """Minimum info needed to pick an assignee: id, name, email, avatar. Nothing else."""
    return jsonify({"users": current_app.extensions["repo"].list_profiles()})
