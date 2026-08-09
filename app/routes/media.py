"""Media capture endpoints: screenshot (screencap) and screen recording."""

from __future__ import annotations

import base64
import logging
import os

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("media", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the media blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


@bp.route("/screencap", methods=["POST"])
def screencap():
    """Capture a screenshot: ``adb screencap -p path``.

    Body: ``{"serial": ..., "path": "..., "encode": "base64"}``.
    When ``encode`` is ``"base64"`` the captured file is read back and its
    base64 contents are returned inline as ``data``.
    """
    body = request.get_json(silent=True) or {}
    serial = body.get("serial")
    path = body.get("path") or "/sdcard/screen.png"
    encode = body.get("encode")

    if not isinstance(path, str):
        return common.fail("BAD_REQUEST", "参数 path 类型错误")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(["screencap", "-p", path], serial)
    result = runner.exec_raw(args, timeout=60.0)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法截屏。", http=500)

    if encode == "base64":
        # Pull the file locally to encode it.
        local_tmp = os.path.join(os.path.dirname(__file__),
                                 "..", "..", "screen_tmp.png")
        pull_args = common.apply_serial(
            ["pull", path, local_tmp], serial)
        pull_result = runner.exec_raw(pull_args, timeout=60.0)
        if pull_result.error or not os.path.exists(local_tmp):
            return common.fail(
                "INTERNAL",
                f"截屏成功但读取文件失败: {pull_result.stderr}",
                http=500,
            )
        with open(local_tmp, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        try:
            os.remove(local_tmp)
        except OSError:
            pass
        return common.ok({"path": path, "data": data})

    return common.ok({
        "path": path,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })


@bp.route("/screenrecord", methods=["POST"])
def screenrecord():
    """Record the screen: ``adb screenrecord --time-limit N path``."""
    body = request.get_json(silent=True) or {}
    serial = body.get("serial")
    path = body.get("path")
    if not path or not isinstance(path, str):
        return common.fail("BAD_REQUEST", "参数 path 缺失或类型错误")

    time_limit = body.get("time_limit", 30)
    if not isinstance(time_limit, (int, float)) or time_limit <= 0:
        time_limit = 30

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(
        ["screenrecord", "--time-limit", str(time_limit), path], serial)
    # Recording may take a while; give a generous timeout.
    result = runner.exec_raw(args, timeout=float(time_limit) + 30.0)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法录屏。", http=500)

    return common.ok({
        "path": path,
        "time_limit": time_limit,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })
