"""ADB HTTP API server entry point.

Supports two modes:

* GUI mode (default): a tkinter window + system tray icon on the main thread,
  with the HTTP server in a daemon thread.
* Headless mode (``--no-gui``): no GUI dependencies are imported at all; the
  process writes its PID to ``--pid-file`` and blocks until signalled.

In headless mode the ``gui`` and ``pystray`` packages are never imported, so
the server can run on machines without a display or those libraries.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys

# Configure a minimal root logger early so imports can log safely.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adb_api.main")


def parse_args(argv: list | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ADB HTTP API server (local-only by default).")
    parser.add_argument("--port", type=int, default=8000,
                        help="HTTP port (default 8000)")
    parser.add_argument("--host", type=str, default=None,
                        help="Bind host (default 127.0.0.1; 0.0.0.0 for LAN)")
    parser.add_argument("--no-gui", action="store_true",
                        help="Run headless without tkinter/pystray")
    parser.add_argument("--log-level", type=str, default="INFO",
                        help="Logging level (DEBUG/INFO/WARNING/ERROR)")
    parser.add_argument("--log-path", type=str, default="adb_api.log",
                        help="Log file path")
    parser.add_argument("--pid-file", type=str, default="adb_api.pid",
                        help="PID file path for headless mode")
    parser.add_argument("--adb-path", type=str, default=None,
                        help="Explicit path to adb executable")
    parser.add_argument("--auth-enabled", action="store_true",
                        help="Enable token auth (placeholder, P2)")
    parser.add_argument("--kill-adb-on-stop", action="store_true",
                        help="Kill adb server on stop (default False)")
    return parser.parse_args(argv)


def write_pid_file(path: str) -> None:
    """Write the current process PID to ``path``."""
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
        logger.info("Wrote PID %s to %s", os.getpid(), path)
    except OSError as exc:
        logger.warning("Could not write PID file %s: %s", path, exc)


def remove_pid_file(path: str) -> None:
    """Best-effort removal of the PID file."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def build_server(config):
    """Assemble Config -> ServerState -> AdbRunner -> ServerApp."""
    from app.config import Config
    from gui.state import ServerState
    from app.server import ServerApp

    state = ServerState()
    server = ServerApp(config, state)
    # create_flask_app wires the ServerApp onto the app config so /shutdown
    # can find it (passed through create_app -> register_all -> health).
    server.create_flask_app()
    return server, state


def main(argv: list | None = None) -> int:
    """Program entry point. Returns a process exit code."""
    args = parse_args(argv)
    from app.config import Config
    config = Config.load_config(args)

    server, state = build_server(config)

    if args.no_gui:
        # Headless: never import gui/pystray.
        pid_file = args.pid_file
        write_pid_file(pid_file)

        def _cleanup(signum, frame):  # noqa: ANN001
            logger.info("Received signal %s, shutting down", signum)
            try:
                server.stop()
            finally:
                remove_pid_file(pid_file)
                sys.exit(0)

        signal.signal(signal.SIGTERM, _cleanup)
        signal.signal(signal.SIGINT, _cleanup)

        logger.info("Starting headless server on %s:%s", config.host,
                    config.port)
        server.start()
        if not server.is_running():
            logger.error("Server failed to start; check %s", config.log_path)
            remove_pid_file(pid_file)
            return 1

        # Block forever (signals handle shutdown).
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            _cleanup(signal.SIGINT, None)
        return 0

    # --- GUI mode: deferred import of tkinter/pystray ---
    from gui.window import MainWindow
    from gui.tray import TrayIcon

    logger.info("Starting GUI server on %s:%s", config.host, config.port)
    window = MainWindow(server, state)
    tray = TrayIcon(server, state, window)
    tray.run()
    window.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
