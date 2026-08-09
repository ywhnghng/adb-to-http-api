"""adb command execution wrapper.

All interaction with the Android Debug Bridge goes through this module. The
single source of truth for locating the ``adb`` executable is
:meth:`AdbRunner.resolve_adb_path`.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Well known error codes surfaced to the API layer.
EXEC_TIMEOUT = "EXEC_TIMEOUT"
INTERNAL = "INTERNAL"
ADB_NOT_FOUND = "ADB_NOT_FOUND"


@dataclass
class AdbResult:
    """Result of running an adb command.

    Attributes:
        stdout: Captured standard output (decoded text).
        stderr: Captured standard error (decoded text).
        exit_code: Process return code (``-1`` on internal failure).
        error: High-level error code (one of the module constants) or ``None``.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    error: Optional[str] = None


class AdbRunner:
    """Runs adb commands via ``subprocess`` against the local adb binary."""

    def __init__(self, adb_path: str) -> None:
        """Initialize the runner.

        Args:
            adb_path: Path to the adb executable. May be empty/None until
                :meth:`ensure_adb` resolves it.
        """
        self.adb_path: str = adb_path or ""
        self.last_error: Optional[str] = None

    @staticmethod
    def resolve_adb_path() -> Optional[str]:
        """Locate the ``adb`` executable on ``PATH``.

        Returns:
            The absolute path to ``adb`` / ``adb.exe`` if found, else ``None``.
        """
        for candidate in ("adb", "adb.exe"):
            resolved = shutil.which(candidate)
            if resolved:
                logger.info("Resolved adb at: %s", resolved)
                return resolved
        logger.warning("adb executable not found on PATH")
        return None

    def ensure_adb(self) -> bool:
        """Ensure adb is available and the server is started.

        Returns:
            ``True`` if a usable adb binary exists (and ``start-server``
            succeeded or was unnecessary); ``False`` otherwise and
            :attr:`last_error` is populated.
        """
        if not self.adb_path:
            path = self.resolve_adb_path()
            if not path:
                self.last_error = ADB_NOT_FOUND
                return False
            self.adb_path = path

        result = self.start_server()
        if result.error is not None:
            self.last_error = result.error
            return False
        return True

    def start_server(self) -> AdbResult:
        """Run ``adb start-server`` to ensure the adb daemon is up.

        Returns:
            An :class:`AdbResult`. On success ``error`` is ``None``.
        """
        if not self.adb_path:
            path = self.resolve_adb_path()
            if not path:
                return AdbResult(error=ADB_NOT_FOUND)
            self.adb_path = path
        return self.exec_raw(["start-server"], timeout=30.0)

    def exec_raw(self,
                 args: List[str],
                 timeout: Optional[float] = 30.0) -> AdbResult:
        """Execute a raw adb command. ``args`` are appended after ``adb``.

        Args:
            args: Argument list (already split, never shell-joined).
            timeout: Per-command timeout in seconds.

        Returns:
            An :class:`AdbResult` describing the outcome.
        """
        if not self.adb_path:
            return AdbResult(error=ADB_NOT_FOUND)

        cmd: List[str] = [self.adb_path, *args]
        logger.debug("Executing: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return AdbResult(
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                exit_code=proc.returncode,
                error=None,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("adb command timed out: %s", args)
            return AdbResult(
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                exit_code=-1,
                error=EXEC_TIMEOUT,
            )
        except FileNotFoundError:
            logger.error("adb binary disappeared: %s", self.adb_path)
            return AdbResult(error=ADB_NOT_FOUND)
        except Exception as exc:  # noqa: BLE001 - surface as INTERNAL
            logger.exception("Unexpected error running adb command")
            return AdbResult(stderr=str(exc), exit_code=-1, error=INTERNAL)
