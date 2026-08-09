"""Blueprint registration for all API routes."""

from __future__ import annotations

from typing import Optional

from flask import Flask

from app.adb_runner import AdbRunner
from gui.state import ServerState


def register_all(app: Flask, runner: AdbRunner, state: ServerState,
                 server=None) -> None:
    """Register every route blueprint onto ``app``.

    Args:
        app: The Flask application.
        runner: Shared adb runner instance.
        state: Shared server state.
        server: Owning :class:`~app.server.ServerApp` (for /shutdown).
    """
    from app.routes import common
    from app.routes import proxy
    from app.routes import device
    from app.routes import apk
    from app.routes import file
    from app.routes import session
    from app.routes import media
    from app.routes import shell
    from app.routes import health
    from app.routes import doc

    # Make the collaborators available to every blueprint import.
    common.set_runner(runner)

    proxy.register(app, runner, state)
    device.register(app, runner, state)
    apk.register(app, runner, state)
    file.register(app, runner, state)
    session.register(app, runner, state)
    media.register(app, runner, state)
    shell.register(app, runner, state)
    health.register(app, runner, state, server)
    doc.register(app)
