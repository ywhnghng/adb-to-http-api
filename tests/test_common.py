"""Unit tests for the shared route helpers in ``app.routes.common``."""

from __future__ import annotations

from flask import Flask

from app.routes import common

# ``ok``/``fail`` call ``flask.jsonify`` which requires an active app context.
_APP = Flask(__name__)


def test_ok_envelope_structure():
    with _APP.app_context():
        resp, code = common.ok({"foo": "bar"})
        data = resp.get_json()

    assert code == 200
    assert data["success"] is True
    assert data["data"] == {"foo": "bar"}
    assert data["error"] is None


def test_fail_envelope_structure():
    with _APP.app_context():
        resp, code = common.fail("BAD_REQUEST", "bad input", http=400)
        data = resp.get_json()

    assert code == 400
    assert data["success"] is False
    assert data["data"] is None
    assert data["error"]["code"] == "BAD_REQUEST"
    assert data["error"]["message"] == "bad input"


def test_apply_serial_skips_when_empty():
    assert common.apply_serial(["devices"], "") == ["devices"]
    assert common.apply_serial(["devices"], None) == ["devices"]


def test_apply_serial_inserts_dash_s_when_present():
    out = common.apply_serial(["devices"], "emulator-5554")
    assert out == ["-s", "emulator-5554", "devices"]


def test_require_auth_is_noop_by_default():
    # Placeholder guard always allows the request through.
    assert common.require_auth() is None
