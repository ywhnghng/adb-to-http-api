<div align="center">

[![中文文档](https://img.shields.io/badge/lang-中文-red)](README_CN.md)
[![English](https://img.shields.io/badge/lang-English-blue)](README.md)

</div>
# ADB HTTP API Server

一个**本机优先**的 Android Debug Bridge（adb）HTTP 服务：通过简洁的 REST API
对连接的 Android 设备执行常用操作（设备列举、安装/卸载 APK、文件推送/拉取、
截屏/录屏、shell、端口转发、重启等）。默认仅监听 `127.0.0.1`，适合本机脚本/
GUI 控制；可选放开到 `0.0.0.0`（仅限可信网络）。

提供两种形态：

- **GUI 模式**（默认）：tkinter 主窗口 + 系统托盘图标，HTTP 服务在后台线程。
- **无头模式**（`--no-gui`）：纯 HTTP 服务，不依赖任何 GUI 库，并通过 PID 文件
  便于停止脚本管理。

---

## 1. 安装

需要 Python 3.11+（开发/打包建议 3.11；本仓库验证环境为 3.13）。

```bash
pip install -r requirements.txt
```

运行时依赖：

- `Flask>=3.0,<4.0`
- `pystray>=0.19,<0.26`（仅 GUI 模式）
- `Pillow>=10.0`（仅 GUI 模式，生成托盘图标）

> `pyinstaller`（打包成 exe）与 `requests`（写外部测试）**不**进运行时依赖。

---

## 2. 前置依赖：adb

本服务通过 `subprocess` 调用本机 `adb`，**不会**自带 adb。

- 下载 Android Platform Tools：
  https://developer.android.com/tools/releases/platform-tools
- 解压并将目录加入系统 `PATH`（确保命令行能直接执行 `adb`）。
- 验证：`adb version` 能正常输出版本信息。

服务启动时会用 `AdbRunner.resolve_adb_path()` 探测 adb；若找不到，`/health`
仍返回 200 但 `adb_available=false`，需要 adb 的接口会返回 `500 ADB_NOT_FOUND`
（含安装指引）。**HTTP 服务本身可正常启动**。

---

## 3. 运行

### 3.1 GUI 模式（默认）

```bash
python main.py
```

会弹出「ADB HTTP 服务」窗口：显示监听地址、运行灯、已连接设备数、滚动日志，
并提供「启动服务 / 停止服务」按钮。关闭窗口会收起到系统托盘（不退出），右键
托盘可「打开主窗口 / 启动服务 / 停止服务 / 退出」。

### 3.2 无头模式（推荐用于脚本/服务化）

```bash
python main.py --no-gui --port 8000
```

- 不导入 `gui` / `pystray`，无 GUI 依赖也可运行。
- 自动将自身 PID 写入 `--pid-file`（默认项目根 `adb_api.pid`）。
- 注册 `SIGTERM` / `SIGINT` 清理逻辑（停止服务 + 删除 PID 文件）。

常用参数：

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--port` | HTTP 端口 | `8000` |
| `--host` | 绑定地址（`0.0.0.0` 放开局域网） | `127.0.0.1` |
| `--no-gui` | 无头模式 | 关 |
| `--log-level` | 日志级别 | `INFO` |
| `--log-path` | 日志文件路径 | `adb_api.log` |
| `--pid-file` | 无头模式 PID 文件 | `adb_api.pid` |
| `--adb-path` | 显式指定 adb 路径 | 自动探测 |
| `--auth-enabled` | 开启鉴权（占位，P2） | 关 |
| `--kill-adb-on-stop` | 停止时 kill adb server | 关 |

---

## 4. 批处理脚本（scripts/）

目录 `scripts/` 下提供两个 bat（中文文件名，GBK + `chcp 65001` 处理）：

- **`启动服务.bat`**：后台以无头模式启动 `main.py --no-gui --port 8000`，
  PID 由 `main.py` 写入项目根 `adb_api.pid`，并提示访问地址。
- **`停止服务.bat`**：读取 `adb_api.pid` 用 `taskkill /PID <pid> /F` 结束进程；
  若系统有 `curl`，先尝试 `POST /shutdown` 优雅关闭；最后删除 PID 文件。

> 双击 `启动服务.bat` 即可在后台运行；双击 `停止服务.bat` 停止。

---

## 5. 打包为 exe（PyInstaller）

锁定使用 **Python 3.11** 环境打包：

```bash
pip install pyinstaller
pyinstaller build.spec
```

产物：`dist/main.exe`（onefile、windowed/无控制台）。双击运行进入 GUI 模式；
托盘可管理启停。

> 注意：在 Python 3.13 等其它版本上也能构建成功，但产出的 exe 为对应版本，
> 与「锁定 3.11」的正式建议有偏差，仅建议开发验证使用。

---

## 6. API 速览

> **在线文档**：服务启动后访问 http://127.0.0.1:8000/doc 获取完整调用指南
> （含给其它 Agent 的说明，内容包括操作说明、接口总表与调用示例）。

所有响应统一外壳：

```json
{ "success": bool, "data": ..., "error": { "code": "...", "message": "..." } | null }
```

### 健康检查 / 控制
- `GET /health` → `{status, adb_available, device_count, running}`
- `POST /shutdown` → 优雅停止服务（停止脚本/控制面用）

### 设备
- `GET /devices` → 解析后的设备列表
- `POST /connect` `{ip, port=5555}`
- `POST /disconnect` `{serial?}`

### 通用代理
- `POST /adb/exec` `{command:"devices -l"}` → 经 `shlex` 拆分后转发

### APK
- `POST /install` `{serial?, path, options?}` （options 例 `["-r","-t"]`）
- `POST /uninstall` `{serial?, package}`

### 文件
- `POST /push` `{serial?, local, remote}`
- `POST /pull` `{serial?, remote, local}`

### 会话 / 控制
- `POST /reboot` `/root` `/unroot` `/remount` `{serial?}`
- `POST /forward` `{serial?, local, remote}`
- `POST /reverse` `{serial?, remote, local}`
- `POST /logcat` `{serial?, lines?=100}` → 取最近 N 行（非流式）

### 媒体
- `POST /screencap` `{serial?, path?, encode?}` （`encode=base64` 返回内联数据）
- `POST /screenrecord` `{serial?, path, time_limit?}`

### Shell
- `POST /shell` `{serial?, command}` → `adb shell <command>`（整体作为单参数）

> 所有「语义」接口均支持可选 `serial`，通过 `-s` 前缀选择多设备中的目标；
> 命令/路径一律以列表方式拼接，规避注入；`shlex` 仅用于 `/adb/exec` 与
> `/shell(split)` 的用户输入拆分。

---

## 7. 环境变量

- `ADB_API_PORT`：覆盖默认端口。
- `ADB_API_HOST`：覆盖默认绑定地址。

---

## 8. 鉴权

默认 `auth_enabled=False`，所有接口无需鉴权（P2 才启用 token）。生产环境如需
暴露到网络，建议配合反向代理做鉴权/TLS，或将 `kill_adb_on_stop` 等敏感操作
限制在本地。

---

## 9. 安全提示

- **默认 `127.0.0.1`**：仅本机可访问，安全。
- 使用 `--host 0.0.0.0` 会监听所有网卡，**仅在可信局域网/经鉴权反向代理后**
  使用，避免把 adb 控制能力暴露给不可信网络。
- 停止服务会导致无法再通过 HTTP 控制设备；`kill_adb_on_stop` 默认关闭，避免
  影响其它依赖 adb 的工具。

---

## 10. 排障

| 现象 | 原因 / 处理 |
| --- | --- |
| 启动报端口冲突 | 改 `--port` 或结束占用进程（见 `停止服务.bat`） |
| 接口返回 `500 ADB_NOT_FOUND` | 本机未安装/未加入 PATH 的 adb；按第 2 节安装 |
| `GET /health` 中 `adb_available=false` | 同上，但 HTTP 服务本身正常 |
| 设备未授权 | 设备端弹窗点「允许」；`adb devices` 显示 `unauthorized` |
| GUI 无法启动（无显示环境） | 用 `--no-gui` 无头模式运行 |
| `python -c "import app"` / `import main` 报错 | 检查 `requirements.txt` 已安装、Python 版本匹配 |

日志写入 `adb_api.log`（可通过 `--log-path` / `--log-level` 调整）。
