"""Lifecycle tests for :class:`app.server.ServerApp`.

Covers ``create_flask_app`` (route registration), the pre-start state of
``is_running``, a safe no-op ``stop`` before start, and a full
start -> running -> stop transition using an ephemeral port.
"""

from __future__ import annotations

import socket

from app.config import Config
from app.server import ServerApp
from gui.state import ServerState


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_create_flask_app_registers_routes():
    config = Config(port=0)
    state = ServerState()
    server = ServerApp(config, state)

    app = server.create_flask_app()

    assert app is server.flask_app
    rules = {str(r) for r in app.url_map.iter_rules()}
    assert "/health" in rules
    assert "/adb/exec" in rules
    assert "/shutdown" in rules
    assert "/devices" in rules


def test_is_running_false_before_start():
    server = ServerApp(Config(), ServerState())
    assert server.is_running() is False


def test_stop_is_safe_before_start():
    server = ServerApp(Config(), ServerState())
    # Must not raise when nothing was started yet.
    server.stop()
    assert server.is_running() is False


def test_start_and_stop_lifecycle():
    port = _free_port()
    config = Config(host="127.0.0.1", port=port)
    state = ServerState()
    server = ServerApp(config, state)
    server.create_flask_app()

    server.start()
    try:
        assert server.is_running() is True
        assert state.running is True
    finally:
        server.stop()

    assert server.is_running() is False
    assert state.running is False
