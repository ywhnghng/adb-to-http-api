@echo off
chcp 65001 >nul
REM ============================================================
REM  ADB HTTP API 服务 - 停止脚本
REM  优先读取项目根 adb_api.pid，taskkill 对应进程；
REM  并附带尝试优雅关闭（POST /shutdown）。
REM ============================================================

SETLOCAL
SET "SCRIPT_DIR=%~dp0"
SET "ROOT_DIR=%SCRIPT_DIR%.."
SET "PID_FILE=%ROOT_DIR%\adb_api.pid"

echo ============================================
echo  ADB HTTP API 服务停止中 ...
echo ============================================

REM 1) 尝试优雅关闭（若 curl 存在）
where curl >nul 2>nul
if %ERRORLEVEL%==0 (
    echo 尝试优雅关闭 (POST /shutdown) ...
    curl -s -X POST http://127.0.0.1:8000/shutdown >nul 2>nul
) else (
    echo 未检测到 curl，跳过优雅关闭。
)

REM 2) 根据 PID 文件强制结束进程
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    echo 读取到 PID: %PID%
    taskkill /PID %PID% /F >nul 2>nul
    if %ERRORLEVEL%==0 (
        echo 已结束进程 %PID%。
    ) else (
        echo 进程 %PID% 不存在或无法结束（可能已退出）。
    )
    del "%PID_FILE%" >nul 2>nul
) else (
    echo 未找到 PID 文件 %PID_FILE%，尝试按端口结束 (8080/8000) ...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
        taskkill /PID %%a /F >nul 2>nul
    )
)

echo 停止操作完成。
echo ============================================
ENDLOCAL
