"""Unit tests for ``app.adb_runner``.

``subprocess.run`` is fully mocked so no real adb binary is required. We cover
the four documented outcomes of :meth:`AdbRunner.exec_raw`:

* success (stdout/stderr/exit_code populated, error is None)
* missing adb path (``error == ADB_NOT_FOUND``)
* timeout (``error == EXEC_TIMEOUT``)
* unexpected exception (``error == INTERNAL``)
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from app.adb_runner import (
    ADB_NOT_FOUND,
    EXEC_TIMEOUT,
    INTERNAL,
    AdbResult,
    AdbRunner,
)


class _FakeCompleted:
    """Mimics ``subprocess.CompletedProcess`` for the happy path."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_exec_raw_success_returns_stdout_stderr_exit_code():
    runner = AdbRunner(adb_path="adb")
    completed = _FakeCompleted(stdout="hello", stderr="warn", returncode=0)
    with patch("app.adb_runner.subprocess.run", return_value=completed) as mock_run:
        result = runner.exec_raw(["devices"])

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    # adb_path must be prepended to the supplied args.
    assert args[0] == ["adb", "devices"]
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True

    assert isinstance(result, AdbResult)
    assert result.stdout == "hello"
    assert result.stderr == "warn"
    assert result.exit_code == 0
    assert result.error is None


def test_exec_raw_missing_adb_path_returns_adb_not_found():
    runner = AdbRunner(adb_path="")
    result = runner.exec_raw(["devices"])
    assert result.error == ADB_NOT_FOUND
    assert result.exit_code == -1


def test_resolve_adb_path_returns_none_when_absent():
    with patch("app.adb_runner.shutil.which", return_value=None):
        assert AdbRunner.resolve_adb_path() is None


def test_resolve_adb_path_returns_candidate():
    with patch("app.adb_runner.shutil.which", return_value="/usr/bin/adb"):
        assert AdbRunner.resolve_adb_path() == "/usr/bin/adb"


def test_exec_raw_timeout_sets_exec_timeout():
    runner = AdbRunner(adb_path="adb")
    with patch(
        "app.adb_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["adb"], timeout=30),
    ) as mock_run:
        result = runner.exec_raw(["devices"], timeout=30)

    mock_run.assert_called_once()
    assert result.error == EXEC_TIMEOUT
    assert result.exit_code == -1


def test_exec_raw_unexpected_exception_sets_internal():
    runner = AdbRunner(adb_path="adb")
    with patch(
        "app.adb_runner.subprocess.run",
        side_effect=RuntimeError("boom"),
    ):
        result = runner.exec_raw(["devices"])

    assert result.error == INTERNAL
    assert result.exit_code == -1
    assert "boom" in result.stderr


def test_exec_raw_file_not_found_sets_adb_not_found():
    runner = AdbRunner(adb_path="adb")
    with patch(
        "app.adb_runner.subprocess.run",
        side_effect=FileNotFoundError(),
    ):
        result = runner.exec_raw(["devices"])
    assert result.error == ADB_NOT_FOUND


def test_ensure_adb_false_when_path_unresolvable():
    runner = AdbRunner(adb_path="")
    with patch("app.adb_runner.AdbRunner.resolve_adb_path", return_value=None):
        ok = runner.ensure_adb()
    assert ok is False
    assert runner.last_error == ADB_NOT_FOUND


def test_ensure_adb_true_when_start_server_succeeds():
    runner = AdbRunner(adb_path="")
    with patch(
        "app.adb_runner.AdbRunner.resolve_adb_path", return_value="/x/adb"
    ), patch(
        "app.adb_runner.subprocess.run",
        return_value=_FakeCompleted(returncode=0),
    ):
        ok = runner.ensure_adb()
    assert ok is True
    assert runner.adb_path == "/x/adb"
    assert runner.last_error is None


def test_start_server_returns_adb_not_found_when_unresolvable():
    runner = AdbRunner(adb_path="")
    with patch("app.adb_runner.AdbRunner.resolve_adb_path", return_value=None):
        result = runner.start_server()
    assert result.error == ADB_NOT_FOUND
