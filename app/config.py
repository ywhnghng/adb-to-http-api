"""Runtime configuration for the ADB HTTP API server.

Configuration flows from three sources (later wins):

1. Sensible built-in defaults defined on :class:`Config`.
2. Environment variables (``ADB_API_PORT``, ``ADB_API_HOST``).
3. Command-line arguments parsed in :func:`main.parse_args`.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Server configuration container.

    Attributes:
        host: Bind address. Defaults to ``127.0.0.1`` (local-only).
        port: TCP port the HTTP server listens on.
        adb_path: Explicit adb executable path; ``None`` triggers auto-resolve.
        log_level: Logging level name (e.g. ``"INFO"``).
        log_path: Path of the rolling/append log file.
        auth_enabled: Whether the ``require_auth`` guard enforces a token.
        kill_adb_on_stop: Whether to kill the adb server when stopping.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    adb_path: str | None = None
    log_level: str = "INFO"
    log_path: str = "adb_api.log"
    auth_enabled: bool = False
    kill_adb_on_stop: bool = False

    @staticmethod
    def from_env() -> "Config":
        """Build a :class:`Config` seeded from environment variables."""
        config = Config()
        env_port = os.environ.get("ADB_API_PORT")
        env_host = os.environ.get("ADB_API_HOST")
        if env_port and env_port.isdigit():
            config.port = int(env_port)
        if env_host:
            config.host = env_host
        return config

    @staticmethod
    def load_config(args: argparse.Namespace | None = None) -> "Config":
        """Build a :class:`Config` from env first, then CLI args.

        Args:
            args: Parsed ``argparse.Namespace`` (may be ``None`` to use env only).

        Returns:
            A fully resolved :class:`Config`.
        """
        config = Config.from_env()
        if args is None:
            return config

        if getattr(args, "host", None):
            config.host = args.host
        if getattr(args, "port", None):
            config.port = args.port
        if getattr(args, "adb_path", None):
            config.adb_path = args.adb_path
        if getattr(args, "log_level", None):
            config.log_level = args.log_level
        if getattr(args, "log_path", None):
            config.log_path = args.log_path
        if getattr(args, "auth_enabled", None) is not None:
            config.auth_enabled = args.auth_enabled
        if getattr(args, "kill_adb_on_stop", None) is not None:
            config.kill_adb_on_stop = args.kill_adb_on_stop
        return config
