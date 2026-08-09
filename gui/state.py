"""Thread-safe shared server state.

The HTTP server thread writes to this state; the tkinter GUI thread reads it
once per second via :meth:`MainWindow.refresh`. All mutations are guarded by a
``threading.Lock`` so concurrent access is safe.
"""

from __future__ import annotations

import threading
from typing import Any, Dict


class ServerState:
    """Shared, thread-safe state between the HTTP server and the GUI."""

    def __init__(self) -> None:
        """Initialize default state values."""
        self._lock = threading.Lock()
        self.running: bool = False
        self.host: str = "127.0.0.1"
        self.port: int = 8000
        self.request_count: int = 0
        self.device_count: int = 0
        self.adb_available: bool = False
        self.last_error: str | None = None
        self.log_lines: list = []

    def update(self, **kwargs: Any) -> None:
        """Update one or more state fields atomically."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def snapshot(self) -> Dict[str, Any]:
        """Return a copy of the current state for safe reading."""
        with self._lock:
            return {
                "running": self.running,
                "host": self.host,
                "port": self.port,
                "request_count": self.request_count,
                "device_count": self.device_count,
                "adb_available": self.adb_available,
                "last_error": self.last_error,
                "log_lines": list(self.log_lines),
            }

    def increment_requests(self) -> None:
        """Atomically increment the served request counter."""
        with self._lock:
            self.request_count += 1

    def append_log(self, line: str, max_lines: int = 200) -> None:
        """Append a log line, trimming to ``max_lines`` entries."""
        with self._lock:
            self.log_lines.append(line)
            if len(self.log_lines) > max_lines:
                self.log_lines = self.log_lines[-max_lines:]
