# ADB HTTP API 服务 · 操作说明与 Agent 调用指南

> 本文件同时是「给运维/脚本人员的操作说明」与「给其它 Agent（程序）的调用指南」。
> 本服务启动后，任何程序访问 `http://127.0.0.1:8000/doc` 即可拿到本文件最新版。

---

## 1. 简介

本服务（ADB HTTP API Server）把本机的 `adb`（Android Debug Bridge）封装为一组
HTTP 接口，让本地脚本、GUI 或自动化 Agent 可以通过发送 HTTP 请求来操控已连接的
Android 设备，而无需自己拼接 `subprocess`、处理设备选择或解析输出。

- 默认监听地址：`http://127.0.0.1:8000`
- 默认仅本机可访问（安全），可选放开到局域网
- 统一 JSON 响应外壳（见第 6 节）
- 绝大多数接口都支持可选 `serial` 参数，用于多设备时指定目标

---

## 2. 给其它 Agent 的关键提示（重要，请先读这段）

> **你（Agent / 程序）只需要知道一件事：**

**只要本服务已启动，访问 `http://127.0.0.1:8000/doc` 就能拿到这份完整指南（也就是
当前这份文件）。** 你无需记住下面的全部细节，先用 HTTP GET 拉取本文件即可获得最新、
最权威的接口说明。

**最通用的入口**是通用代理接口：

```
POST /adb/exec
Content-Type: application/json
{ "command": "<任意 adb 子命令，字符串形式>" }
```

- 例如 `{ "command": "devices -l" }` 等价于在命令行执行 `adb devices -l`。
- 该接口会用 `shlex` 拆分命令字符串后透传给本机 `adb`，因此**几乎任何 adb 功能
  都能通过它完成**，不必逐一对接下面的语义化接口。
- 返回 `{"stdout": "...", "stderr": "...", "exit_code": 0}`（见第 4、6 节）。

**调用这些接口只需要发送 HTTP 请求**，无需 SDK、无需登录（默认无鉴权）。推荐做法：

- 用你所在语言的 HTTP 客户端（Python `requests`、Node `fetch`、curl 等）发请求。
- 请求体统一为 JSON（`Content-Type: application/json`）。
- 多设备场景，在语义化接口里带上 `"serial": "<设备序列号>"`（见第 4 节 `serial?` 说明）。

**最小化上手示例（伪代码）：**

```python
import requests

BASE = "http://127.0.0.1:8000"

# 1) 先确认服务活着，并探测 adb 是否可用
health = requests.get(f"{BASE}/health").json()

# 2) 最通用：直接透传任意 adb 命令
r = requests.post(f"{BASE}/adb/exec",
                  json={"command": "devices -l"}).json()
print(r["data"]["stdout"])

# 3) 或调用语义化接口
r = requests.post(f"{BASE}/install",
                  json={"path": "app.apk", "options": ["-r", "-t"]}).json()
```

如果 `127.0.0.1:8000` 连不上，通常是服务没启动或端口被改了（见第 8 节配置 / 第 7 节排障）。

---

## 3. 快速开始（操作说明）

### 3.1 前置依赖：安装 adb

本服务通过 `subprocess` 调用本机 `adb`，**不会**自带 adb。请先在本机准备：

1. 下载 Android Platform Tools（含 `adb`）：
   https://developer.android.com/tools/releases/platform-tools
2. 解压并把目录加入系统 `PATH`（确保命令行能直接执行 `adb`）。
3. 验证：在命令行运行 `adb version` 能正常输出版本信息即可。

> 若找不到 adb，HTTP 服务本身仍可正常启动；需要 adb 的接口会返回
> `500 ADB_NOT_FOUND`（含安装指引）。`/health` 会返回 `adb_available=false`。

### 3.2 三种启动方式

| 方式 | 适用场景 | 启动命令 / 操作 |
| --- | --- | --- |
| ① bat 包（推荐日常） | 已就绪，双击即用 | 双击 `scripts/启动服务.bat`，默认监听 `127.0.0.1:8000` |
| ② exe（GUI，分发给无 Python 环境） | 无 Python 的 Windows 机器 | `pyinstaller build.spec` 构建后双击 `dist/main.exe`，GUI 点「启动服务」 |
| ③ 源码（推荐开发/脚本） | 有 Python 环境 | `pip install -r requirements.txt` 后 `python main.py --no-gui --port 8000` |

**① bat 包**

- `scripts/启动服务.bat`：后台以无头模式启动 `main.py --no-gui --port 8000`，
  并提示访问地址。
- `scripts/停止服务.bat`：按 PID 文件优雅停止（先尝试 `POST /shutdown`，再
  `taskkill`），最后清理 `adb_api.pid`。
- 双击对应 bat 即可，无需命令行。

**② exe（GUI + 系统托盘）**

1. 在 Python 3.11 环境构建（见第 10 节）：`pyinstaller build.spec --noconfirm`
   → 生成 `dist/main.exe`。
2. 双击 `dist/main.exe` 进入 GUI 模式，点击「启动服务」。
3. 关闭窗口会收起至系统托盘（不退出）；右键托盘可「打开主窗口 / 启动服务 /
   停止服务 / 退出」。
4. 退出请使用托盘右键「退出」（不要直接 X 关闭，那只是最小化到托盘）。

**③ 源码无头模式**

```bash
pip install -r requirements.txt
python main.py --no-gui --port 8000
```

- 不导入 `gui`/`pystray`，无 GUI 依赖也可运行。
- 将自身 PID 写入 `adb_api.pid`（可用 `--pid-file` 指定），便于脚本停止。
- 监听 `SIGTERM`/`SIGINT` 做优雅清理（停止服务 + 删除 PID 文件）。

### 3.3 停止方式

- **bat 包**：双击 `scripts/停止服务.bat`。
- **exe / GUI**：系统托盘右键「退出」。
- **源码 / 任意形态**：发送 `POST /shutdown`（优雅关闭），或结束进程（bat 包会
  读 PID 文件 `taskkill`）。

---

## 4. 接口总表

> 约定：`serial?` 表示**可选**字段。填了会用 `-s <serial>` 指定目标设备；
> 多设备时必须填（否则 adb 无法判断操作哪台）。不填则对当前唯一（默认）设备操作。
> 所有请求体为 JSON，`Content-Type: application/json`。

### 健康检查 / 控制

| Method | Path | 请求体 | 说明 / 响应示例 |
| --- | --- | --- | --- |
| GET | `/health` | 无 | 探活。`{"status","adb_available","device_count","running"}` |
| POST | `/shutdown` | 无 | 优雅停止服务。`{"success":true}` |

`/health` 示例响应：

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "adb_available": true,
    "device_count": 1,
    "running": true
  },
  "error": null
}
```

### 通用代理（最通用的入口）

| Method | Path | 请求体 | 说明 / 响应示例 |
| --- | --- | --- | --- |
| POST | `/adb/exec` | `{"command":"devices -l"}` | 透传任意 adb 子命令（字符串，按 `shlex` 拆分） |

响应：

```json
{
  "success": true,
  "data": { "stdout": "List of devices attached\n...", "stderr": "", "exit_code": 0 },
  "error": null
}
```

### 设备

| Method | Path | 请求体 | 说明 |
| --- | --- | --- | --- |
| GET | `/devices` | 无 | 已连接设备列表 `{"devices":[{"serial","state"}]}` |
| POST | `/connect` | `{"ip":"192.168.1.10","port":5555}` | TCP 无线连接，返回 `{"serial","state"}` |
| POST | `/disconnect` | `{"serial":"192.168.1.10:5555"}` | 断开无线连接，返回 `{"serial","disconnected"}` |

### APK

| Method | Path | 请求体 | 说明 |
| --- | --- | --- | --- |
| POST | `/install` | `{"serial?":null,"path":"app.apk","options":["-r","-t"]}` | 安装 APK，`options` 为可选 adb 参数列表 |
| POST | `/uninstall` | `{"serial?":null,"package":"com.demo"}` | 卸载应用 |

### 文件

| Method | Path | 请求体 | 说明 |
| --- | --- | --- | --- |
| POST | `/push` | `{"serial?":null,"local":"/a.txt","remote":"/sdcard/a.txt"}` | 本机 → 设备 |
| POST | `/pull` | `{"serial?":null,"remote":"/sdcard/a.txt","local":"/tmp/a.txt"}` | 设备 → 本机 |

### 会话 / 控制

| Method | Path | 请求体 | 说明 |
| --- | --- | --- | --- |
| POST | `/reboot` | `{"serial?":null}` | 重启设备 |
| POST | `/root` | `{"serial?":null}` | `adb root` |
| POST | `/unroot` | `{"serial?":null}` | `adb unroot` |
| POST | `/remount` | `{"serial?":null}` | `adb remount` |
| POST | `/forward` | `{"serial?":null,"local":"tcp:11111","remote":"tcp:22222"}` | 端口转发 |
| POST | `/reverse` | `{"serial?":null,"remote":"tcp:22222","local":"tcp:11111"}` | 反向转发 |
| POST | `/logcat` | `{"serial?":null,"lines?":100}` | 取最近 N 行 logcat（非流式） |

### 媒体

| Method | Path | 请求体 | 说明 |
| --- | --- | --- | --- |
| POST | `/screencap` | `{"serial?":null,"path":"/sdcard/a.png","encode?":"base64"}` | 截屏；`encode=base64` 返回内联 `data` |
| POST | `/screenrecord` | `{"serial?":null,"path":"/sdcard/r.mp4","time_limit?":10}` | 录屏（秒） |

`/screencap` 响应（`encode=base64` 时）：

```json
{ "success": true, "data": { "path": "/sdcard/a.png", "data": "<base64...>" }, "error": null }
```

### Shell

| Method | Path | 请求体 | 说明 |
| --- | --- | --- | --- |
| POST | `/shell` | `{"serial?":null,"command":"pm list packages"}` | `adb shell <command>`（整体作为单参数） |

响应：`{"stdout","stderr","exit_code"}`（同 `/adb/exec`）。

---

## 5. 调用示例（给 Agent 参考）

> 注意：在 shell/curl 里写 JSON 时，字符串内的引号要用 `\` 转义（如 `"{\"command\":\"devices -l\"}"`）。
> 在程序里请直接用 JSON 对象（如 Python `requests.post(url, json={...})`），
> 由库负责编码，避免手动拼接。

### 5.1 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 5.2 通用代理（透传任意 adb 命令）

```bash
curl -X POST http://127.0.0.1:8000/adb/exec \
  -H "Content-Type: application/json" \
  -d "{\"command\":\"devices -l\"}"
```

### 5.3 无线连接设备

```bash
curl -X POST http://127.0.0.1:8000/connect \
  -H "Content-Type: application/json" \
  -d "{\"ip\":\"192.168.1.10\",\"port\":5555}"
```

### 5.4 断开无线设备

```bash
curl -X POST http://127.0.0.1:8000/disconnect \
  -H "Content-Type: application/json" \
  -d "{\"serial\":\"192.168.1.10:5555\"}"
```

### 5.5 安装 APK（带可选参数）

```bash
curl -X POST http://127.0.0.1:8000/install \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"app.apk\",\"options\":[\"-r\",\"-t\"]}"
```

### 5.6 执行 shell 命令

```bash
curl -X POST http://127.0.0.1:8000/shell \
  -H "Content-Type: application/json" \
  -d "{\"command\":\"pm list packages\"}"
```

### 5.7 程序内调用（Python 伪代码）

```python
import requests

BASE = "http://127.0.0.1:8000"

# 通用代理
r = requests.post(f"{BASE}/adb/exec", json={"command": "devices -l"})
print(r.json()["data"]["stdout"])

# 语义化：安装到指定设备
r = requests.post(f"{BASE}/install",
                  json={"serial": "192.168.1.10:5555",
                        "path": "app.apk",
                        "options": ["-r", "-t"]})
print(r.json())
```

---

## 6. 统一响应结构

所有接口（除 `GET /doc` 返回纯文本 markdown 外）都遵循如下外壳：

```json
{
  "success": true,
  "data": <任意>,
  "error": { "code": "字符串错误码", "message": "人类可读说明" } | null
}
```

- 成功：`success = true`，`data` 为接口业务数据，`error = null`。
- 失败：`success = false`，`data = null`，`error` 含 `code` 与 `message`。

`GET /doc` 是例外：它返回 `Content-Type: text/markdown; charset=utf-8` 的纯文本
Markdown（便于 Agent 解析 / 浏览器直接查看），不是 JSON。

---

## 7. 错误与排障

| 现象 | 原因 / 处理 |
| --- | --- |
| `POST /adb/exec` 返回 `500` + `ADB_NOT_FOUND` | 本机未安装/未加入 PATH 的 adb；按第 3.1 节安装 |
| 参数缺失 / 类型错误 | 返回 `400` + `BAD_REQUEST`（如 `/adb/exec` 的 `command` 缺失） |
| 命令执行超时 | 返回 `500` + `EXEC_TIMEOUT` |
| 服务内部异常 | 返回 `500` + `INTERNAL` |
| 启动报端口冲突 | 改 `--port` 或结束占用进程（见 `停止服务.bat`） |
| `GET /health` 中 `adb_available=false` | adb 未就绪，但 HTTP 服务本身正常 |
| `GET /doc` 返回 `404` + `DOC_NOT_FOUND` | 文档文件未随服务部署（源码形态应在 `docs/` 下；exe 形态打包时须含 `datas`） |

错误码一览：`ADB_NOT_FOUND` / `BAD_REQUEST` / `EXEC_TIMEOUT` / `INTERNAL` /
`DOC_NOT_FOUND`（各码见 `error.code` 字段）。

---

## 8. 配置

默认绑定 `host=127.0.0.1`、`port=8000`。可用以下方式覆盖：

- 命令行：
  - `--host 0.0.0.0` 放开局域网（仅可信网络使用）。
  - `--port 8080` 改端口。
- 环境变量：
  - `ADB_API_PORT` 覆盖默认端口。
  - `ADB_API_HOST` 覆盖默认绑定地址。
- 其它参数：`--log-level`、`--log-path`、`--pid-file`、`--adb-path`、
  `--auth-enabled`（占位，P2 才启用）、`--kill-adb-on-stop`。

示例：

```bash
python main.py --no-gui --host 0.0.0.0 --port 8080
# 或
ADB_API_HOST=0.0.0.0 ADB_API_PORT=8080 python main.py --no-gui
```

---

## 9. 安全提示

- **默认 `127.0.0.1`**：仅本机可访问，安全。
- **默认无鉴权**（`auth_enabled=False`，P2 才启用 token）。`GET /doc`、所有接口
  均不要求凭据，任何能访问该端口的程序都可调用——因此务必限制访问范围。
- 使用 `--host 0.0.0.0` 会监听所有网卡，**仅在可信局域网或经鉴权反向代理后**使用，
  切勿暴露到公网。
- 建议在可信网络内使用；如需公网/跨网络访问，请前置带鉴权与 TLS 的反向代理。

---

## 10. 打包为 exe（PyInstaller）

锁定使用 **Python 3.11** 环境打包，确保产出的 `dist/main.exe` 版本一致：

```bash
pip install pyinstaller
pyinstaller build.spec --noconfirm
```

产物：`dist/main.exe`（onefile、windowed/无控制台）。双击进入 GUI 模式。

> 注意：`build.spec` 的 `datas` 已包含 `docs/AGENT_API_GUIDE.md`，因此打包后
> `GET /doc` 仍能找到并返回本指南。在 Python 3.13 等其它版本上也能构建成功，但
> 产出的 exe 为对应版本，与「锁定 3.11」的正式建议有偏差，仅建议开发验证使用。

---

*本指南由服务自身通过 `GET /doc` 暴露，内容与服务版本保持一致。*
