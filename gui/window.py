"""tkinter main window for the ADB HTTP service.

The window shows live server status, a scrolling log view and start/stop
buttons. It polls :class:`~gui.state.ServerState` once per second via
``root.after`` and never touches tkinter widgets from the HTTP thread.
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import scrolledtext, ttk

from gui.state import ServerState

logger = logging.getLogger(__name__)


class MainWindow:
    """tkinter front-end for starting/stopping and monitoring the server."""

    def __init__(self, server, state: ServerState) -> None:
        """Initialize the window.

        Args:
            server: The :class:`~app.server.ServerApp` to control.
            state: Shared server state polled for status.
        """
        self.server = server
        self.state = state

        self.root = tk.Tk()
        self.root.title("ADB HTTP 服务")
        self.root.geometry("420x320")
        self.root.resizable(False, False)

        self._build_widgets()

        # Close / minimize hides to tray instead of quitting.
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start the polling loop.
        self.refresh()

    def _build_widgets(self) -> None:
        """Construct the status area, log box and control buttons."""
        # --- Status frame ---
        status_frame = ttk.LabelFrame(self.root, text="服务状态",
                                      padding=(10, 6))
        status_frame.pack(fill=tk.X, padx=10, pady=(10, 6))

        self.status_light = tk.Label(status_frame, text="●",
                                     fg="red", font=("Arial", 14))
        self.status_light.grid(row=0, column=0, padx=(0, 8))

        self.addr_label = ttk.Label(status_frame,
                                    text="监听地址: --")
        self.addr_label.grid(row=0, column=1, sticky=tk.W)

        self.dev_label = ttk.Label(status_frame, text="已连接设备: 0")
        self.dev_label.grid(row=1, column=1, sticky=tk.W, pady=(2, 0))

        self.adb_label = ttk.Label(status_frame, text="ADB: 未知")
        self.adb_label.grid(row=2, column=1, sticky=tk.W, pady=(2, 0))

        # --- Log frame ---
        log_frame = ttk.LabelFrame(self.root, text="日志",
                                   padding=(10, 6))
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=10, state=tk.DISABLED,
            font=("Consolas", 9))
        self.log_box.pack(fill=tk.BOTH, expand=True)

        # --- Button frame ---
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.start_btn = ttk.Button(btn_frame, text="启动服务",
                                    command=self.on_start)
        self.start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.stop_btn = ttk.Button(btn_frame, text="停止服务",
                                   command=self.on_stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

    def on_start(self) -> None:
        """Start the server and toggle button states."""
        self.server.start()
        self._set_buttons(running=True)

    def on_stop(self) -> None:
        """Stop the server and toggle button states."""
        self.server.stop()
        self._set_buttons(running=False)

    def _set_buttons(self, running: bool) -> None:
        """Enable/disable start/stop buttons based on running state."""
        if running:
            self.start_btn.configure(state=tk.DISABLED)
            self.stop_btn.configure(state=tk.NORMAL)
        else:
            self.start_btn.configure(state=tk.NORMAL)
            self.stop_btn.configure(state=tk.DISABLED)

    def refresh(self) -> None:
        """Poll state and update widgets. Scheduled via root.after(1000)."""
        snap = self.state.snapshot()
        running = snap["running"]

        # Status light.
        self.status_light.configure(fg="green" if running else "red")
        addr = f"{snap['host']}:{snap['port']}" if snap["host"] else "--"
        self.addr_label.configure(text=f"监听地址: {addr}")
        self.dev_label.configure(text=f"已连接设备: {snap['device_count']}")
        self.adb_label.configure(
            text=f"ADB: {'可用' if snap['adb_available'] else '不可用'}")

        self._set_buttons(running=running)

        # Append any new log lines.
        if snap["log_lines"]:
            self.log_box.configure(state=tk.NORMAL)
            for line in snap["log_lines"]:
                self.log_box.insert(tk.END, line + "\n")
            self.log_box.see(tk.END)
            self.log_box.configure(state=tk.DISABLED)
            # Clear processed lines so we only append new ones next tick.
            self.state.update(log_lines=[])

        if snap["last_error"]:
            self.log_box.configure(state=tk.NORMAL)
            self.log_box.insert(tk.END, f"[错误] {snap['last_error']}\n")
            self.log_box.see(tk.END)
            self.log_box.configure(state=tk.DISABLED)

        # Reschedule.
        self.root.after(1000, self.refresh)

    def _on_close(self) -> None:
        """Hide to tray instead of destroying the window."""
        self.root.withdraw()

    def run(self) -> None:
        """Enter the tkinter main loop."""
        self.root.mainloop()
