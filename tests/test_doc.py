"""Tests for the ``GET /doc`` online documentation endpoint.

Uses Flask's test client with injected fakes so no real adb or device is
required. The endpoint should return the raw markdown guide (``text/markdown``)
and the document must contain the key markers used by other Agents.
"""

from __future__ import annotations

import os

from unittest.mock import MagicMock

from app import create_app
from app.config import Config
from app.routes.doc import DOC_DIR, DOC_FILENAME
from app.routes.doc import _resolve_doc_path
from gui.state import ServerState


class FakeRunner:
    """Minimal stand-in for :class:`AdbRunner`; doc route does not use it."""

    adb_path = "adb"

    def ensure_adb(self) -> bool:  # noqa: D401
        return True


class FakeServerApp:
    """Stand-in for :class:`app.server.ServerApp`."""

    def __init__(self):
        self.stop = MagicMock()


def _make_app():
    config = Config()
    state = ServerState()
    app = create_app(config, state, FakeRunner(), FakeServerApp())
    app.config["TESTING"] = True
    return app


def test_resolve_doc_path_finds_guide_in_source_tree():
    # When run from the project root, the document must be discovered.
    path = _resolve_doc_path()
    assert path is not None
    assert path.endswith(os.path.join(DOC_DIR, DOC_FILENAME))
    assert os.path.isfile(path)


def test_doc_returns_200_with_text_markdown_content_type():
    app = _make_app()
    client = app.test_client()

    resp = client.get("/doc")

    assert resp.status_code == 200
    content_type = resp.headers.get("Content-Type", "")
    assert "text/markdown" in content_type
    assert "charset=utf-8" in content_type.lower()


def test_doc_body_contains_key_markers():
    app = _make_app()
    client = app.test_client()

    resp = client.get("/doc")
    body = resp.get_data(as_text=True)

    # Markers an Agent would look for to confirm this is the right guide.
    assert "ADB" in body
    assert "/adb/exec" in body
    assert "127.0.0.1:8000" in body


def test_doc_route_registered_on_app():
    app = _make_app()
    rules = {str(r) for r in app.url_map.iter_rules()}
    assert "/doc" in rules
