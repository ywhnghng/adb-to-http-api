"""File push / pull endpoints."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("file", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the file blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


@bp.route("/push", methods=["POST"])
def push():
    """Push a local file to the device: ``adb push local remote``."""
    body = request.get_json(silent=True) or {}
    local = body.get("local")
    remote = body.get("remote")
    if not local or not isinstance(local, str):
        return common.fail("BAD_REQUEST", "参数 local 缺失或类型错误")
    if not remote or not isinstance(remote, str):
        return common.fail("BAD_REQUEST", "参数 remote 缺失或类型错误")

    serial = body.get("serial")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(["push", local, remote], serial)
    result = runner.exec_raw(args, timeout=120.0)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法推送文件。", http=500)

    return common.ok({
        "local": local,
        "remote": remote,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })


@bp.route("/pull", methods=["POST"])
def pull():
    """Pull a remote file from the device: ``adb pull remote local``."""
    body = request.get_json(silent=True) or {}
    remote = body.get("remote")
    local = body.get("local")
    if not remote or not isinstance(remote, str):
        return common.fail("BAD_REQUEST", "参数 remote 缺失或类型错误")
    if not local or not isinstance(local, str):
        return common.fail("BAD_REQUEST", "参数 local 缺失或类型错误")

    serial = body.get("serial")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(["pull", remote, local], serial)
    result = runner.exec_raw(args, timeout=120.0)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法拉取文件。", http=500)

    return common.ok({
        "remote": remote,
        "local": local,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })
