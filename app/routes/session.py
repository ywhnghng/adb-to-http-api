"""Session / device-control endpoints.

Covers rebooting, root/unroot, remount, port forwarding/reverse and a
non-streaming tail of logcat (last N lines).
"""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("session", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the session blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


def _simple_command(subcommand: list, serial):
    """Run a serial-prefixed adb command and return a JSON response."""
    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(subcommand, serial)
    result = runner.exec_raw(args)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法执行该操作。", http=500)

    return common.ok({
        "command": " ".join(subcommand),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })


@bp.route("/reboot", methods=["POST"])
def reboot():
    """Reboot the device: ``adb reboot``."""
    body = request.get_json(silent=True) or {}
    return _simple_command(["reboot"], body.get("serial"))


@bp.route("/root", methods=["POST"])
def root():
    """Restart adbd as root: ``adb root``."""
    body = request.get_json(silent=True) or {}
    return _simple_command(["root"], body.get("serial"))


@bp.route("/unroot", methods=["POST"])
def unroot():
    """Restart adbd as non-root: ``adb unroot``."""
    body = request.get_json(silent=True) or {}
    return _simple_command(["unroot"], body.get("serial"))


@bp.route("/remount", methods=["POST"])
def remount():
    """Remount /system read-write: ``adb remount``."""
    body = request.get_json(silent=True) or {}
    return _simple_command(["remount"], body.get("serial"))


@bp.route("/forward", methods=["POST"])
def forward():
    """Set up a port forward: ``adb forward local remote``."""
    body = request.get_json(silent=True) or {}
    local = body.get("local")
    remote = body.get("remote")
    if not local or not isinstance(local, str):
        return common.fail("BAD_REQUEST", "参数 local 缺失或类型错误")
    if not remote or not isinstance(remote, str):
        return common.fail("BAD_REQUEST", "参数 remote 缺失或类型错误")

    serial = body.get("serial")
    return _simple_command(["forward", local, remote], serial)


@bp.route("/reverse", methods=["POST"])
def reverse():
    """Set up a reverse socket: ``adb reverse remote local``."""
    body = request.get_json(silent=True) or {}
    remote = body.get("remote")
    local = body.get("local")
    if not remote or not isinstance(remote, str):
        return common.fail("BAD_REQUEST", "参数 remote 缺失或类型错误")
    if not local or not isinstance(local, str):
        return common.fail("BAD_REQUEST", "参数 local 缺失或类型错误")

    serial = body.get("serial")
    return _simple_command(["reverse", remote, local], serial)


@bp.route("/logcat", methods=["POST"])
def logcat():
    """Return the last N lines of logcat (non-streaming).

    Body: ``{"serial": "...", "lines": 100}``. Implemented as
    ``adb logcat -d | tail -n lines``.
    """
    body = request.get_json(silent=True) or {}
    serial = body.get("serial")
    lines = body.get("lines", 100)
    if not isinstance(lines, int) or lines <= 0:
        lines = 100

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None

    # Build the base logcat -d command (handled by adb, no shell).
    base_args = common.apply_serial(["logcat", "-d"], serial)

    # Run adb directly and slice the last N lines in Python. This avoids any
    # dependency on the platform `tail` binary (absent on Windows) and the
    # risk of a hung shell pipeline.
    result = runner.exec_raw(base_args, timeout=60.0)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法读取 logcat。",
                           http=500)
    if result.error is not None:
        return common.fail("INTERNAL", f"读取 logcat 失败: {result.error}",
                           http=500)

    out = "\n".join(result.stdout.splitlines()[-lines:])
    return common.ok({
        "serial": serial,
        "lines": lines,
        "log": out,
        "stderr": result.stderr,
    })
