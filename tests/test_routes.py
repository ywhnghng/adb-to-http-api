"""Integration-style route tests using Flask's test client.

A fake :class:`AdbRunner` is injected into the app so no real adb binary or
device is required. The fake records every ``exec_raw`` call so we can also
assert that ``apply_serial`` correctly inserts ``-s <serial>``.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app import create_app
from app.adb_runner import ADB_NOT_FOUND, AdbResult
from app.config import Config
from gui.state import ServerState


class FakeRunner:
    """A stand-in for :class:`AdbRunner` that never touches subprocess."""

    def __init__(self, adb_path: str = "adb", available: bool = True,
                 result: AdbResult | None = None):
        self.adb_path = adb_path
        self._available = available
        self.result = result or AdbResult(
            stdout="ok", stderr="", exit_code=0, error=None)
        self.calls: list = []

    def ensure_adb(self) -> bool:
        return self._available

    def exec_raw(self, args, timeout=30.0) -> AdbResult:
        self.calls.append((list(args), timeout))
        return self.result


class FakeServerApp:
    """Stand-in for :class:`app.server.ServerApp`, exposing a mock stop()."""

    def __init__(self):
        self.stop = MagicMock()


def _make_app(runner: FakeRunner, server: FakeServerApp | None = None):
    config = Config()
    state = ServerState()
    app = create_app(config, state, runner, server)
    app.config["TESTING"] = True
    return app, state


@pytest.fixture
def client():
    runner = FakeRunner()
    server = FakeServerApp()
    app, state = _make_app(runner, server)
    return app.test_client(), runner, server, state


# --- /adb/exec (proxy) -----------------------------------------------------

def test_adb_exec_success_transparent(client):
    c, runner, _, _ = client
    runner.result = AdbResult(
        stdout="List of devices attached", stderr="", exit_code=0, error=None)
    resp = c.post("/adb/exec", json={"command": "devices -l"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["stdout"] == "List of devices attached"
    assert data["data"]["exit_code"] == 0
    # command string was split by shlex into ["devices", "-l"].
    assert runner.calls[-1][0] == ["devices", "-l"]


def test_adb_exec_parses_quoted_command(client):
    c, runner, _, _ = client
    resp = c.post("/adb/exec", json={"command": 'shell "ls -l"'})
    data = resp.get_json()

    assert resp.status_code == 200
    # Quoted token stays together: shell + "ls -l".
    assert runner.calls[-1][0] == ["shell", "ls -l"]


def test_adb_exec_missing_command_returns_400(client):
    c, _, _, _ = client
    resp = c.post("/adb/exec", json={})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["error"]["code"] == "BAD_REQUEST"


def test_adb_exec_blank_command_returns_400(client):
    c, _, _, _ = client
    resp = c.post("/adb/exec", json={"command": "   "})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["error"]["code"] == "BAD_REQUEST"


def test_adb_exec_adb_unavailable_returns_500_adb_not_found():
    # Separate app whose runner reports NO adb path -> ensure_adb_ready fails.
    runner = FakeRunner(adb_path="")
    app, _ = _make_app(runner)
    c = app.test_client()

    resp = c.post("/adb/exec", json={"command": "devices"})
    data = resp.get_json()

    assert resp.status_code == 500
    assert data["error"]["code"] == ADB_NOT_FOUND


# --- /health ---------------------------------------------------------------

def test_health_returns_200_with_expected_fields(client):
    c, runner, _, state = client
    runner.result = AdbResult(
        stdout="List of devices attached\ndevice1\tdevice\n",
        stderr="", exit_code=0, error=None)
    state.running = True

    resp = c.get("/health")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    d = data["data"]
    assert "adb_available" in d
    assert "device_count" in d
    assert "running" in d
    assert d["adb_available"] is True
    assert d["device_count"] == 1
    assert d["running"] is True
    assert d["status"] == "ok"


# --- /shutdown -------------------------------------------------------------

def test_shutdown_invokes_server_stop(client):
    c, _, server, _ = client
    resp = c.post("/shutdown")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    server.stop.assert_called_once()


# --- semantic endpoints ----------------------------------------------------

def test_devices_parses_output(client):
    c, runner, _, _ = client
    runner.result = AdbResult(
        stdout="List of devices attached\nemulator-5554\tdevice\n",
        stderr="", exit_code=0, error=None)
    resp = c.get("/devices")
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["count"] == 1
    assert data["data"]["devices"][0]["serial"] == "emulator-5554"
    assert data["data"]["devices"][0]["status"] == "device"


def test_install_missing_path_returns_400(client):
    c, _, _, _ = client
    resp = c.post("/install", json={})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["error"]["code"] == "BAD_REQUEST"


def test_install_success_and_no_serial(client):
    c, runner, _, _ = client
    resp = c.post("/install", json={"path": "/tmp/a.apk"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["path"] == "/tmp/a.apk"
    assert "exit_code" in data["data"]
    # No serial supplied -> apply_serial must NOT prepend "-s".
    assert runner.calls[-1][0] == ["install", "/tmp/a.apk"]


def test_install_with_serial_inserts_dash_s(client):
    c, runner, _, _ = client
    resp = c.post("/install", json={"path": "/tmp/a.apk", "serial": "DEV1"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert runner.calls[-1][0][:2] == ["-s", "DEV1"]


def test_shell_success(client):
    c, _, _, _ = client
    resp = c.post("/shell", json={"command": "ls /data/local/tmp"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["command"] == "ls /data/local/tmp"
    assert "stdout" in data["data"]


def test_shell_missing_command_returns_400(client):
    c, _, _, _ = client
    resp = c.post("/shell", json={})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["error"]["code"] == "BAD_REQUEST"


def test_uninstall_success(client):
    c, _, _, _ = client
    resp = c.post("/uninstall", json={"package": "com.example.app"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["package"] == "com.example.app"


def test_push_success(client):
    c, _, _, _ = client
    resp = c.post("/push", json={"local": "/a", "remote": "/b"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert "exit_code" in data["data"]


def test_pull_success(client):
    c, _, _, _ = client
    resp = c.post("/pull", json={"remote": "/b", "local": "/a"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True


def test_connect_missing_ip_returns_400(client):
    c, _, _, _ = client
    resp = c.post("/connect", json={})
    data = resp.get_json()
    assert resp.status_code == 400
    assert data["error"]["code"] == "BAD_REQUEST"


def test_disconnect_success(client):
    c, _, _, _ = client
    resp = c.post("/disconnect", json={"serial": "DEV1"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert "exit_code" in data["data"]


def test_reboot_success(client):
    c, _, _, _ = client
    resp = c.post("/reboot", json={})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True


def test_root_unroot_remount_success(client):
    c, _, _, _ = client
    for endpoint in ("/root", "/unroot", "/remount"):
        resp = c.post(endpoint, json={})
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True


def test_forward_success(client):
    c, _, _, _ = client
    resp = c.post("/forward", json={"local": "tcp:1111", "remote": "tcp:2222"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert "exit_code" in data["data"]


def test_reverse_success(client):
    c, _, _, _ = client
    resp = c.post("/reverse", json={"remote": "tcp:2222", "local": "tcp:1111"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True


def test_logcat_returns_last_n_lines(client):
    c, runner, _, _ = client
    log_text = "\n".join(f"line{i}" for i in range(200))
    runner.result = AdbResult(stdout=log_text, stderr="", exit_code=0, error=None)
    resp = c.post("/logcat", json={"lines": 10})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["lines"] == 10
    lines = data["data"]["log"].splitlines()
    assert len(lines) == 10
    assert lines[-1] == "line199"


def test_screencap_success(client):
    c, _, _, _ = client
    resp = c.post("/screencap", json={"path": "/sdcard/a.png"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["path"] == "/sdcard/a.png"


def test_screenrecord_success(client):
    c, _, _, _ = client
    resp = c.post("/screenrecord", json={"path": "/sdcard/r.mp4"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["data"]["path"] == "/sdcard/r.mp4"
