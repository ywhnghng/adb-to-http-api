"""Health and control endpoints: liveness probe and shutdown hook."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app

from app.routes import common
from app.adb_runner import AdbRunner

logger = logging.getLogger(__name__)

bp = Blueprint("health", __name__)

# Reference to the ServerApp, injected at registration time.
_SERVER_APP = None


def register(app, runner: AdbRunner, state, server=None) -> None:  # noqa: ANN001
    """Register the health blueprint onto ``app``.

    Args:
        app: The Flask application.
        runner: Shared adb runner instance.
        state: Shared server state.
        server: Owning :class:`~app.server.ServerApp`; stored so ``/shutdown``
            can gracefully stop the server.
    """
    global _SERVER_APP
    _SERVER_APP = server if server is not None else app.config.get("server_app")
    common.set_runner(runner)
    app.register_blueprint(bp)


@bp.route("/health", methods=["GET"])
def health():
    """Return a liveness/health snapshot.

    Response includes adb availability, device count and running flag. Device
    count is best-effort; failures degrade gracefully to 0.
    """
    state = current_app.config.get("server_state")
    runner = common.get_runner()

    adb_available = bool(runner and runner.adb_path and runner.ensure_adb())
    device_count = 0
    if adb_available and runner is not None:
        result = runner.exec_raw(["devices"], timeout=10.0)
        if result.error is None:
            # Count lines that look like device entries (skip header/blank).
            for line in result.stdout.splitlines()[1:]:
                if line.strip() and not line.startswith("*"):
                    device_count += 1

    running = bool(state and state.running)
    status = "ok" if running else "error"

    return common.ok({
        "status": status,
        "adb_available": adb_available,
        "device_count": device_count,
        "running": running,
    })


@bp.route("/shutdown", methods=["POST"])
def shutdown():
    """Stop the HTTP server (used by the control panel / stop script).

    Returns ``{"success": true}``. The stop script may also simply kill the
    process via the PID file; this endpoint is the graceful alternative.
    """
    if _SERVER_APP is not None:
        try:
            _SERVER_APP.stop()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error stopping server via /shutdown")
            return common.fail("INTERNAL", f"停止服务失败: {exc}", http=500)
    return common.ok({"success": True})
