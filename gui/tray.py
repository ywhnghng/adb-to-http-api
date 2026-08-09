"""System tray icon integration using pystray + PIL.

A small colored icon (green = running, gray = stopped) is generated in memory
with Pillow so no external icon assets are required. The module imports
``pystray`` and ``PIL`` at module load time; it is only imported in GUI mode
(see ``main.py`` which defers all gui imports when ``--no-gui`` is used).
"""

from __future__ import annotations

import logging

from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

from gui.state import ServerState
from gui.window import MainWindow

logger = logging.getLogger(__name__)


class TrayIcon:
    """System tray controller for the ADB HTTP service."""

    def __init__(self, server, state: ServerState, window: MainWindow) -> None:
        """Initialize the tray icon.

        Args:
            server: The :class:`~app.server.ServerApp` to control.
            state: Shared server state (used to pick icon color).
            window: The :class:`MainWindow` to show/hide on click.
        """
        self.server = server
        self.state = state
        self.window = window
        self.icon: Icon | None = None
        self._running_color = (60, 180, 75)   # green
        self._stopped_color = (150, 150, 150)  # gray

    def _make_icon(self, color: tuple) -> Image.Image:
        """Render a simple 64x64 circle icon in the given RGB color."""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, 56, 56), fill=(*color, 255))
        return img

    def _icon_for_state(self) -> Image.Image:
        """Pick the icon matching the current running state."""
        snap = self.state.snapshot()
        return self._make_icon(
            self._running_color if snap["running"] else self._stopped_color)

    def _on_open(self, icon, item) -> None:
        """Restore (de-iconify) the main window."""
        self.window.root.deiconify()
        self.window.root.lift()

    def _on_start(self, icon, item) -> None:
        """Start the server from the tray menu."""
        if not self.state.snapshot()["running"]:
            self.server.start()

    def _on_stop(self, icon, item) -> None:
        """Stop the server from the tray menu."""
        if self.state.snapshot()["running"]:
            self.server.stop()

    def _on_quit(self, icon, item) -> None:
        """Stop the server (if running) and close the GUI."""
        try:
            if self.state.snapshot()["running"]:
                self.server.stop()
        except Exception:  # noqa: BLE001
            logger.exception("Error stopping server on quit")
        self.window.root.destroy()
        if self.icon is not None:
            self.icon.stop()

    def run(self) -> None:
        """Build and run the tray icon (blocking)."""
        menu = Menu(
            MenuItem("打开主窗口", self._on_open),
            Menu.SEPARATOR,
            MenuItem("启动服务", self._on_start),
            MenuItem("停止服务", self._on_stop),
            Menu.SEPARATOR,
            MenuItem("退出", self._on_quit),
        )
        self.icon = Icon(
            "adb_http_server",
            icon=self._icon_for_state(),
            title="ADB HTTP 服务",
            menu=menu,
        )

        # Single-click restores the window.
        self.icon.on_click = lambda icon, event: self._on_open(icon, None)

        # Periodically refresh the icon color to reflect running state.
        self.icon.run_detached()
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        """Update tray icon color every 2s to match server state."""
        if self.icon is None:
            return
        try:
            self.icon.icon = self._icon_for_state()
        except Exception:  # noqa: BLE001
            logger.debug("Tray icon refresh skipped")
        self.window.root.after(2000, self._schedule_refresh)
