@echo off
chcp 65001 >nul
REM ============================================================
REM  ADB HTTP API 服务 - 启动脚本（无头模式）
REM  双击本文件即可在后台启动服务；PID 由 main.py 写入项目根的 adb_api.pid
REM ============================================================

SETLOCAL
SET "SCRIPT_DIR=%~dp0"
REM 项目根目录（scripts 的上上一级）
SET "ROOT_DIR=%SCRIPT_DIR%.."

REM 选取可用的 Python：优先 C:\python（自带 Flask+tkinter），否则回退 python
SET "PYTHON_EXE=C:\python\python.exe"
IF NOT EXIST "%PYTHON_EXE%" SET "PYTHON_EXE=python"

echo ============================================
echo  ADB HTTP API 服务启动中 ...
echo  监听地址: http://127.0.0.1:8000
echo  Python: %PYTHON_EXE%
echo ============================================

REM 切到项目根，避免 PID/日志路径错位；用独立最小化窗口启动，关闭启动窗不影响服务
cd /d "%ROOT_DIR%"
start "" /MIN "%PYTHON_EXE%" "%ROOT_DIR%\main.py" --no-gui --port 8000 --pid-file "%ROOT_DIR%\adb_api.pid"

echo 服务已在后台启动（独立窗口，已最小化到任务栏）。
echo 健康检查: http://127.0.0.1:8000/health
echo 接口文档: http://127.0.0.1:8000/doc
echo 停止请运行: 停止服务.bat
echo ============================================
ENDLOCAL
