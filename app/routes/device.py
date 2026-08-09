"""Device management endpoints: list, connect, disconnect.

Parses the output of ``adb devices -l`` into a structured list so clients do
not have to parse adb's text format themselves.
"""

from __future__ import annotations

import logging
import re

from flask import Blueprint, request

from app.routes import common
from app.adb_runner import ADB_NOT_FOUND

logger = logging.getLogger(__name__)

bp = Blueprint("device", __name__)


def register(app, runner, state) -> None:  # noqa: ANN001
    """Register the device blueprint onto ``app``."""
    common.set_runner(runner)
    app.register_blueprint(bp)


def _parse_devices_output(text: str) -> list:
    """Parse ``adb devices -l`` output into a list of device dicts."""
    devices = []
    lines = text.splitlines()
    # Skip the header line "List of devices attached".
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial = parts[0]
        status = parts[1]
        # Remaining tokens are key:value attributes (e.g. model:Phone).
        attrs = {}
        for token in parts[2:]:
            if ":" in token:
                key, _, value = token.partition(":")
                attrs[key] = value
        devices.append({
            "serial": serial,
            "status": status,
            "attrs": attrs,
        })
    return devices


@bp.route("/devices", methods=["GET"])
def list_devices():
    """Return connected devices parsed from ``adb devices -l``."""
    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    result = runner.exec_raw(["devices", "-l"])
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法列举设备。", http=500)

    devices = _parse_devices_output(result.stdout)
    return common.ok({"devices": devices, "count": len(devices)})


@bp.route("/connect", methods=["POST"])
def connect():
    """Connect to a network device via ``adb connect ip:port``."""
    body = request.get_json(silent=True) or {}
    ip = body.get("ip")
    if not ip or not isinstance(ip, str):
        return common.fail("BAD_REQUEST", "参数 ip 缺失或类型错误")

    port = body.get("port", 5555)
    if not isinstance(port, int):
        return common.fail("BAD_REQUEST", "参数 port 必须为整数")

    target = f"{ip}:{port}"

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    result = runner.exec_raw(["connect", target])
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法连接设备。", http=500)

    return common.ok({
        "target": target,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })


@bp.route("/disconnect", methods=["POST"])
def disconnect():
    """Disconnect from a device via ``adb disconnect [serial]``."""
    body = request.get_json(silent=True) or {}
    serial = body.get("serial")

    not_ready = common.ensure_adb_ready()
    if not_ready is not None:
        return not_ready

    runner = common.get_runner()
    assert runner is not None
    args = ["disconnect"]
    if serial:
        args.append(serial)
    result = runner.exec_raw(args)
    if result.error == ADB_NOT_FOUND:
        return common.fail(ADB_NOT_FOUND, "未找到 adb，无法断开设备。", http=500)

    return common.ok({
        "serial": serial,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
    })
