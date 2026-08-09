"""APK install / uninstall endpoints."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("apk", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the apk blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


@bp.route("/install", methods=["POST"])
def install():
    """Install an APK: ``adb install [options] path``."""
    body = request.get_json(silent=True) or {}
    path = body.get("path")
    if not path or not isinstance(path, str):
        return common.fail("BAD_REQUEST", "参数 path 缺失或类型错误")

    serial = body.get("serial")
    options = body.get("options") or []
    if not isinstance(options, list):
        return common.fail("BAD_REQUEST", "参数 options 必须为列表")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(["install", *options, path], serial)
    result = runner.exec_raw(args)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法安装 APK。", http=500)

    return common.ok({
        "path": path,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })


@bp.route("/uninstall", methods=["POST"])
def uninstall():
    """Uninstall a package: ``adb uninstall package``."""
    body = request.get_json(silent=True) or {}
    package = body.get("package")
    if not package or not isinstance(package, str):
        return common.fail("BAD_REQUEST", "参数 package 缺失或类型错误")

    serial = body.get("serial")
    options = body.get("options") or []
    if not isinstance(options, list):
        return common.fail("BAD_REQUEST", "参数 options 必须为列表")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = common.apply_serial(["uninstall", *options, package], serial)
    result = runner.exec_raw(args)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法卸载应用。", http=500)

    return common.ok({
        "package": package,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })
