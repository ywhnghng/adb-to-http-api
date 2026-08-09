"""ADB HTTP API Server application package.

This package exposes a thin factory ``create_app`` and a ``register_all``
helper so the server bootstrap code can assemble a Flask application driven
by a :class:`~app.config.Config`, a shared :class:`~gui.state.ServerState`
and an :class:`~app.adb_runner.AdbRunner`.
"""

from __future__ import annotations

from typing import Optional

from flask import Flask

from app.config import Config
from app.adb_runner import AdbRunner
from gui.state import ServerState


def create_app(config: Config,
               state: ServerState,
               runner: Optional[AdbRunner] = None,
               server: Optional["ServerApp"] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config: Resolved runtime configuration.
        state: Shared, thread-safe server state used by the GUI and routes.
        runner: Optional pre-built :class:`AdbRunner`. If omitted a runner is
            created from ``config.adb_path`` (may be ``None`` until resolved).
        server: Optional owning :class:`~app.server.ServerApp`; recorded on the
            app config so ``/shutdown`` can stop the server.

    Returns:
        A fully configured :class:`flask.Flask` instance with all blueprints
        registered.
    """
    app = Flask(__name__)
    app.config.from_object(config)

    if runner is None:
        adb_path = config.adb_path or AdbRunner.resolve_adb_path() or ""
        runner = AdbRunner(adb_path=adb_path)

    # Stash collaborators on the app so routes can reach them.
    app.config["adb_runner"] = runner
    app.config["server_state"] = state
    if server is not None:
        app.config["server_app"] = server

    from app.routes import register_all
    register_all(app, runner, state, server)
    return app


def register_all(app: Flask, runner: AdbRunner, state: ServerState,
                 server: Optional["ServerApp"] = None) -> None:
    """Register every blueprint onto ``app``.

    Convenience re-export; the authoritative implementation lives in
    :mod:`app.routes`. Kept here for back-compat with the design contract.
    """
    from app.routes import register_all as _register_all
    _register_all(app, runner, state, server)
