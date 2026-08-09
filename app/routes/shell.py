"""Arbitrary shell command endpoint.

Runs ``adb shell <command>``. The command is passed as a single argument to
``shell`` to avoid ambiguity with token splitting/injection. ``shlex`` is used
only if the caller explicitly requests splitting via the ``split`` flag.
"""

from __future__ import annotations

import logging
import shlex

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("shell", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the shell blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


@bp.route("/shell", methods=["POST"])
def shell():
    """Run a shell command on the device.

    Body: ``{"serial": ..., "command": "ls /data/local/tmp"}``.
    The command is passed verbatim as a single argument to ``adb shell``.
    If ``split=true`` is provided, the command string is split with shlex and
    passed as separate arguments instead.
    """
    body = request.get_json(silent=True) or {}
    command = body.get("command")
    if not command or not isinstance(command, str):
        return common.fail("BAD_REQUEST", "参数 command 缺失或类型错误")

    serial = body.get("serial")
    split = bool(body.get("split", False))

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None

    if split:
        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            return common.fail("BAD_REQUEST", f"命令解析失败: {exc}")
        args = common.apply_serial(["shell", *tokens], serial)
    else:
        # Pass the whole command as a single argument to adb shell.
        args = common.apply_serial(["shell", command], serial)

    result = runner.exec_raw(args, timeout=60.0)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法执行 shell。", http=500)

    return common.ok({
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })
