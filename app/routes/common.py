"""Shared helpers for API routes: response envelope, runner access, auth.

All route modules import from here so that the JSON response shape stays
consistent across the whole API.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, List, Optional

from flask import jsonify, request

from app.adb_runner import AdbRunner, ADB_NOT_FOUND

logger = logging.getLogger(__name__)

# Module-level reference to the shared runner (set by register_all).
_RUNNER: Optional[AdbRunner] = None


def set_runner(runner: AdbRunner) -> None:
    """Inject the shared :class:`AdbRunner` used by :func:`get_runner`."""
    global _RUNNER
    _RUNNER = runner


def get_runner() -> Optional[AdbRunner]:
    """Return the shared :class:`AdbRunner` (possibly unresolved)."""
    return _RUNNER


def ok(data: Any = None, code: int = 200):
    """Build a successful JSON response.

    Envelope: ``{"success": true, "data": ..., "error": null}``.
    """
    return jsonify({"success": True, "data": data, "error": None}), code


def fail(error_code: str, message: str, http: int = 400):
    """Build a failure JSON response.

    Envelope: ``{"success": false, "data": null, "error": {...}}``.
    """
    return jsonify({
        "success": False,
        "data": None,
        "error": {"code": error_code, "message": message},
    }), http


def apply_serial(args: List[str], serial: Optional[str]) -> List[str]:
    """Prepend ``-s <serial>`` to ``args`` when a serial is provided.

    Args:
        args: Base adb argument list.
        serial: Optional device serial. When falsy it is ignored.

    Returns:
        A new argument list with ``-s serial`` inserted at the front, or the
        original list when ``serial`` is empty.
    """
    if serial:
        return ["-s", serial, *args]
    return list(args)


def require_auth() -> Optional[tuple]:
    """Placeholder auth guard.

    When ``auth_enabled`` is ``False`` (the default) this is a no-op. When
    enabled (future P2 work) it should validate a bearer token; for now it
    always allows the request through and returns ``None``.

    Returns:
        ``None`` to indicate the request may proceed, or a Flask response
        tuple to reject it.
    """
    # TODO(P2): implement token validation when auth_enabled becomes True.
    return None


def ensure_adb_ready() -> Optional[tuple]:
    """Ensure adb is available; return a fail() tuple if not.

    Returns:
        ``None`` when adb is ready, otherwise a tuple suitable for returning
        directly from a route (``fail(...)`` response).
    """
    runner = get_runner()
    if runner is None or not runner.adb_path:
        return fail(
            ADB_NOT_FOUND,
            "未找到 adb 可执行文件。请在系统 PATH 中安装 Android Platform "
            "Tools（adb），或启动时通过 --adb-path 指定路径。下载地址："
            "https://developer.android.com/tools/releases/platform-tools",
            http=500,
        )
    if not runner.ensure_adb():
        return fail(
            ADB_NOT_FOUND,
            "adb 已找到但无法启动 adb server，请检查 PATH 与环境。错误："
            f"{runner.last_error or '未知'}",
            http=500,
        )
    return None
