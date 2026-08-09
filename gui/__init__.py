"""GUI package: tkinter window + pystray system tray.

The GUI runs on the main thread while the HTTP server runs in a daemon
thread. They communicate only through :class:`gui.state.ServerState`.
"""

from gui.state import ServerState

__all__ = ["ServerState"]
