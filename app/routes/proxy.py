"""Generic adb command proxy endpoint.

Exposes ``POST /adb/exec`` which accepts a raw command string, splits it with
``shlex`` and forwards it to adb. This is the lowest-level escape hatch for
clients that need adb functionality not covered by the structured endpoints.
"""

from __future__ import annotations

import logging
import shlex

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("proxy", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the proxy blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


@bp.route("/adb/exec", methods=["POST"])
def adb_exec():
    """Execute a raw adb command provided by the client.

    Body: ``{"command": "devices -l"}``.
    """
    body = request.get_json(silent=True) or {}
    command = body.get("command")
    if not command or not isinstance(command, str):
        return common.fail("BAD_REQUEST", "参数 command 缺失或类型错误")

    try:
        args = shlex.split(command)
    except ValueError as exc:
        return common.fail("BAD_REQUEST", f"命令解析失败: {exc}")

    if not args:
        return common.fail("BAD_REQUEST", "参数 command 为空")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    result = runner.exec_raw(args)

    if result.error == ADB_NOT_FOUND:
        return common.fail(
            ADB_NOT_FOUND,
            "未找到 adb 可执行文件。请安装 Android Platform Tools 并加入 PATH。",
            http=500,
        )

    return common.ok({
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })
