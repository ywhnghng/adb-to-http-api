"""HTTP server lifecycle and Flask app assembly.

The server runs inside a dedicated daemon thread using Werkzeug's
``make_server`` so the adb command calls (which may block) never block the
GUI event loop. Shared :class:`~gui.state.ServerState` is the only channel
between the HTTP thread and the tkinter main thread.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

from werkzeug.serving import make_server

from app.config import Config
from gui.state import ServerState

logger = logging.getLogger(__name__)


class ServerApp:
    """Owns the Flask app and its background serving thread."""

    def __init__(self, config: Config, state: ServerState) -> None:
        """Initialize.

        Args:
            config: Runtime configuration (host/port/log settings).
            state: Shared server state (thread-safe).
        """
        self.config = config
        self.state = state
        self.flask_app = None
        self._server = None
        self._thread: Optional[threading.Thread] = None

    def create_flask_app(self):
        """Build the Flask application with all routes registered.

        Returns:
            The configured :class:`flask.Flask` instance.
        """
        from app import create_app
        from app.adb_runner import AdbRunner

        adb_path = self.config.adb_path or AdbRunner.resolve_adb_path() or ""
        runner = AdbRunner(adb_path=adb_path)
        self.flask_app = create_app(self.config, self.state, runner, self)
        self._setup_logging()
        return self.flask_app

    def start(self) -> None:
        """Start the HTTP server in a daemon thread.

        On bind failure the error is recorded in ``state.last_error`` and the
        thread exits cleanly without crashing the process.
        """
        if self.flask_app is None:
            self.create_flask_app()

        self.state.running = True
        self.state.host = self.config.host
        self.state.port = self.config.port

        try:
            self._server = make_server(
                self.config.host,
                self.config.port,
                self.flask_app,
                threaded=True,
            )
        except OSError as exc:
            logger.error("Failed to bind %s:%s - %s",
                         self.config.host, self.config.port, exc)
            self.state.running = False
            self.state.last_error = f"绑定地址失败: {exc}"
            return

        self._thread = threading.Thread(
            target=self._serve, name="adb-http-server", daemon=True)
        self._thread.start()
        logger.info("HTTP server started on %s:%s",
                    self.config.host, self.config.port)

    def _serve(self) -> None:
        """Thread target: serve requests until shutdown."""
        try:
            assert self._server is not None
            self._server.serve_forever()
        except Exception:  # noqa: BLE001
            logger.exception("HTTP server loop crashed")
            self.state.last_error = "HTTP 服务线程异常退出"
        finally:
            self.state.running = False

    def stop(self) -> None:
        """Stop the HTTP server and join the serving thread."""
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Error during server shutdown")
            self._server = None

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

        self.state.running = False
        logger.info("HTTP server stopped")

    def is_running(self) -> bool:
        """Return whether the server is currently running."""
        return self.state.running and self._server is not None

    def _setup_logging(self) -> None:
        """Configure the ``adb_api`` logger with file (+ optional console)."""
        log = logging.getLogger("adb_api")
        if log.handlers:
            return  # already configured once

        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        log.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        try:
            file_handler = logging.FileHandler(self.config.log_path,
                                               encoding="utf-8")
            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)
        except Exception:  # noqa: BLE001
            logger.warning("Could not attach file handler for %s",
                           self.config.log_path)

        # Promote adb_api to also print to console for easier debugging.
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        log.addHandler(console)
