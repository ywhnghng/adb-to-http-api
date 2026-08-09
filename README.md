ADB HTTP API Server
A local-first Android Debug Bridge (adb) HTTP service: perform common operations on connected Android devices via a concise REST API (device enumeration, APK install/uninstall, file push/pull, screenshot/screen recording, shell commands, port forwarding, reboot, etc.). By default, it listens only on 127.0.0.1, making it suitable for local scripts/GUI control; it can optionally be exposed to 0.0.0.0 (trusted networks only).
Available in two modes:
GUI Mode (Default): tkinter main window + system tray icon, with the HTTP service running in a background thread.
Headless Mode (--no-gui): Pure HTTP service with no GUI library dependencies, managed via a PID file for easy stopping.
1. Installation
Requires Python 3.11+ (3.11 recommended for development/packaging; this repository is verified on 3.13).
bash

pip install -r requirements.txt
Runtime dependencies:
Flask>=3.0,<4.0
pystray>=0.19,<0.26 (GUI mode only)
Pillow>=10.0 (GUI mode only, for generating tray icons)
pyinstaller (for exe packaging) and requests (for external testing) are not runtime dependencies.
2. Prerequisites: adb
This service invokes the local adb via subprocess and does not bundle adb itself.
Download Android Platform Tools:
https://developer.android.com/tools/releases/platform-tools
Extract the archive and add the directory to your system PATH (ensure adb can be executed directly from the command line).
Verify: adb version should output version information correctly.
On startup, the service uses AdbRunner.resolve_adb_path() to detect adb. If not found, /health still returns 200 but with adb_available=false. Endpoints requiring adb will return 500 ADB_NOT_FOUND (including installation instructions). The HTTP service itself will start normally.
3. Running
3.1 GUI Mode (Default)
bash

python main.py
An "ADB HTTP Service" window will appear, displaying the listening address, status indicator, connected device count, and scrolling logs. It provides "Start Service / Stop Service" buttons. Closing the window minimizes it to the system tray (does not exit). Right-click the tray icon to "Open Main Window / Start Service / Stop Service / Exit".
3.2 Headless Mode (Recommended for scripts/services)
bash

python main.py --no-gui --port 8000
Does not import gui / pystray; runs without any GUI dependencies.
Automatically writes its PID to --pid-file (defaults to adb_api.pid in the project root).
Registers SIGTERM / SIGINT cleanup handlers (stops service + deletes PID file).
Common arguments:

Argument	Description	Default
--port	HTTP port	8000
--host	Bind address (0.0.0.0 to expose to LAN)	127.0.0.1
--no-gui	Headless mode	Off
--log-level	Log level	INFO
--log-path	Log file path	adb_api.log
--pid-file	PID file for headless mode	adb_api.pid
--adb-path	Explicitly specify adb path	Auto-detect
--auth-enabled	Enable authentication (placeholder, P2)	Off
--kill-adb-on-stop	Kill adb server on stop	Off
4. Batch Scripts (scripts/)
The scripts/ directory provides two batch files (Chinese filenames, handled via GBK + chcp 65001):
启动服务.bat (Start Service): Starts main.py --no-gui --port 8000 in the background. The PID is written to adb_api.pid in the project root by main.py, and the access URL is displayed.
停止服务.bat (Stop Service): Reads adb_api.pid and terminates the process using taskkill /PID <pid> /F. If curl is available, it first attempts a graceful shutdown via POST /shutdown. Finally, it deletes the PID file.
Double-click 启动服务.bat to run in the background; double-click 停止服务.bat to stop.
5. Packaging as EXE (PyInstaller)
Lock to Python 3.11 environment for packaging:
bash

pip install pyinstaller
pyinstaller build.spec
Output: dist/main.exe (onefile, windowed/no console). Double-click to run in GUI mode; manage start/stop via the system tray.
Note: Building on other versions like Python 3.13 may succeed, but the resulting exe will correspond to that version, deviating from the official "locked to 3.11" recommendation. Use other versions for development verification only.
6. API Overview
Online Documentation: After starting the service, visit http://127.0.0.1:8000/doc for the complete usage guide (includes instructions for other Agents, operation manuals, full endpoint list, and call examples).
All responses follow a unified envelope:
json

{ "success": bool, "data": ..., "error": { "code": "...", "message": "..." } | null }
Health Check / Control
GET /health → {status, adb_available, device_count, running}
POST /shutdown → Gracefully stop the service (for stop scripts/control plane)
Devices
GET /devices → Parsed device list
POST /connect {ip, port=5555}
POST /disconnect {serial?}
Generic Proxy
POST /adb/exec {command:"devices -l"} → Split via shlex and forwarded
APK
POST /install {serial?, path, options?} (options e.g., ["-r","-t"])
POST /uninstall {serial?, package}
Files
POST /push {serial?, local, remote}
POST /pull {serial?, remote, local}
Session / Control
POST /reboot/root/unroot/remount {serial?}
POST /forward {serial?, local, remote}
POST /reverse {serial?, remote, local}
POST /logcat {serial?, lines?=100} → Fetch last N lines (non-streaming)
Media
POST /screencap {serial?, path?, encode?} (encode=base64 returns inline data)
POST /screenrecord {serial?, path, time_limit?}
Shell
POST /shell {serial?, command} → adb shell <command> (passed as a single argument)
All semantic endpoints support an optional serial parameter to target specific devices in multi-device setups via the -s prefix. Commands/paths are always concatenated as lists to prevent injection. shlex is used solely for splitting user input in /adb/exec and /shell(split).
7. Environment Variables
ADB_API_PORT: Override default port.
ADB_API_HOST: Override default bind address.
8. Authentication
By default, auth_enabled=False; all endpoints require no authentication (token auth enabled in P2). For production environments exposed to the network, it is recommended to use a reverse proxy for authentication/TLS, or restrict sensitive operations like kill_adb_on_stop to localhost.
9. Security Notes
Default 127.0.0.1: Accessible only locally; secure.
Using --host 0.0.0.0 listens on all network interfaces. Use only in trusted LANs or behind an authenticated reverse proxy to avoid exposing adb control capabilities to untrusted networks.
Stopping the service prevents further HTTP control of devices. kill_adb_on_stop is disabled by default to avoid affecting other tools relying on adb.
10. Troubleshooting

Symptom	Cause / Solution
Port conflict on startup	Change --port or kill the occupying process (see 停止服务.bat)
Endpoint returns 500 ADB_NOT_FOUND	adb not installed or not in PATH; install per Section 2
adb_available=false in GET /health	Same as above, but HTTP service itself is running normally
Device unauthorized	Click "Allow" on the device popup; adb devices shows unauthorized
GUI fails to start (no display environment)	Run in headless mode with --no-gui
python -c "import app" / import main errors	Verify requirements.txt is installed and Python version matches
Logs are written to adb_api.log (configurable via --log-path / --log-level).

