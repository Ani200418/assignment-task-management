"""Application factory. Dependencies (repo, sender, verifier) can be injected, which is how tests run
the real Flask app without Supabase or Gmail."""
import logging
import time

from flask import Flask, g, jsonify, request
from flask_cors import CORS

from app.config import Config
from app.middleware.auth import TokenVerifier
from app.routes import health, internal, tasks
from app.services.email_service import GmailSender
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService
from app.utils.errors import ApiError


def create_app(config: Config | None = None, repo=None, sender=None, verifier=None) -> Flask:
    config = config or Config.from_env()
    app = Flask(__name__)
    app.config.update(CRON_SECRET=config.cron_secret, MAX_CONTENT_LENGTH=100 * 1024)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if repo is None:
        config.validate()
        from app.repositories.supabase_repository import SupabaseRepository
        repo = SupabaseRepository(config.supabase_url, config.supabase_service_role_key)
    sender = sender or GmailSender(config)
    notifier = NotificationService(repo, sender)
    app.extensions.update(
        repo=repo, notifier=notifier, task_service=TaskService(repo, notifier),
        token_verifier=verifier or TokenVerifier(config.supabase_url),
    )

    CORS(app, resources={r"/api/*": {"origins": list(config.cors_origins)}},
         allow_headers=["Authorization", "Content-Type"], methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])

    app.register_blueprint(health.bp, url_prefix="/api")
    app.register_blueprint(tasks.bp, url_prefix="/api/tasks")
    app.register_blueprint(internal.bp, url_prefix="/api/internal")

    @app.before_request
    def _start():
        g.t0 = time.perf_counter()

    @app.after_request
    def _log(resp):
        user = getattr(g, "user", None)
        # Log method, path, status, time and user id ONLY. Never headers (they hold tokens) or bodies.
        app.logger.info("%s %s -> %s %.0fms user=%s", request.method, request.path, resp.status_code,
                        (time.perf_counter() - g.t0) * 1000, user.id if user else "-")
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        return resp

    @app.errorhandler(ApiError)
    def _api_error(e):
        return e.to_response()

    @app.errorhandler(404)
    def _404(_):
        return {"error": {"code": "not_found", "message": "Not found"}}, 404

    @app.errorhandler(405)
    def _405(_):
        return {"error": {"code": "method_not_allowed", "message": "Method not allowed"}}, 405

    @app.errorhandler(413)
    def _413(_):
        return {"error": {"code": "payload_too_large", "message": "Request body too large"}}, 413

    @app.errorhandler(Exception)
    def _500(e):
        app.logger.exception("Unhandled error")      # full detail goes to the server log only
        return jsonify({"error": {"code": "internal_error", "message": "Something went wrong"}}), 500

    return app
