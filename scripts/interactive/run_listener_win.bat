@echo off
REM ============================================================
REM 日生研 NSKSD · Windows 飞书长连接监听器启动器（V9.8 重写）
REM
REM 修复测试报告踩坑：
REM   - 问题 #12 A：虚拟环境路径硬编码 → 每次启动前校验 venv/Scripts/python.exe
REM   - 问题 #12 B：lark-oapi 缺失 → ensure_venv 自动 pip install
REM   - 问题 #12 C：LARK_APP_ID 未注入 → 从 config.json / scripts/.env 自动加载
REM
REM 用法：run_listener_win.bat [start|stop|status|restart|logs]
REM ============================================================
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

cd /d "%~dp0"
set VENV_DIR=.venv
set LOG_FILE=listener.out
set PID_FILE=listener.pid
set PYTHON_EXE=%VENV_DIR%\Scripts\python.exe
set PIP_EXE=%VENV_DIR%\Scripts\pip.exe

REM ---- 从 config.json / .env 注入凭证（问题 #12 C） ----
set CONFIG_JSON=%USERPROFILE%\.nsksd-content\config.json
if exist "%CONFIG_JSON%" (
    for /f "usebackq delims=" %%A in (`python -c "import json,sys; cfg=json.load(open(r'%CONFIG_JSON%',encoding='utf-8')); lark=cfg.get('lark',{}); print(lark.get('app_id','')+'|'+lark.get('app_secret','')+'|'+lark.get('target_open_id','')+'|'+lark.get('customer_open_chat_id',''))" 2^>nul`) do (
        for /f "tokens=1-4 delims=|" %%a in ("%%A") do (
            if not "%%a"=="" if not "%%a"=="REPLACE_ME" set LARK_APP_ID=%%a
            if not "%%b"=="" if not "%%b"=="REPLACE_ME" set LARK_APP_SECRET=%%b
            if not "%%c"=="" if not "%%c"=="REPLACE_ME" set TARGET_OPEN_ID=%%c
            if not "%%d"=="" if not "%%d"=="REPLACE_ME" set TARGET_CHAT_ID=%%d
        )
    )
)

REM fallback 1：scripts/.env
set ENV_FILE=%~dp0..\.env
if exist "%ENV_FILE%" (
    for /f "usebackq tokens=1,2 delims==" %%A in ("%ENV_FILE%") do (
        if "%%A"=="LARK_APP_ID" if "!LARK_APP_ID!"=="" set LARK_APP_ID=%%B
        if "%%A"=="LARK_APP_SECRET" if "!LARK_APP_SECRET!"=="" set LARK_APP_SECRET=%%B
        if "%%A"=="TARGET_OPEN_ID" if "!TARGET_OPEN_ID!"=="" set TARGET_OPEN_ID=%%B
        if "%%A"=="TARGET_CHAT_ID" if "!TARGET_CHAT_ID!"=="" set TARGET_CHAT_ID=%%B
        if "%%A"=="FEISHU_APP_ID" if "!LARK_APP_ID!"=="" set LARK_APP_ID=%%B
        if "%%A"=="FEISHU_APP_SECRET" if "!LARK_APP_SECRET!"=="" set LARK_APP_SECRET=%%B
    )
)

REM UTF-8 强制输出（问题 #11）
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if "%1"=="" set ACTION=start
if not "%1"=="" set ACTION=%1

if "%ACTION%"=="start"   goto :start
if "%ACTION%"=="stop"    goto :stop
if "%ACTION%"=="status"  goto :status
if "%ACTION%"=="restart" goto :restart
if "%ACTION%"=="logs"    goto :logs
echo 用法: %0 [start^|stop^|status^|restart^|logs]
exit /b 1

:start
if "%LARK_APP_ID%"=="" (
    echo [错误] LARK_APP_ID 未设置。请先运行: python scripts\setup_cli.py
    exit /b 2
)
if "%LARK_APP_SECRET%"=="" (
    echo [错误] LARK_APP_SECRET 未设置。请先运行: python scripts\setup_cli.py
    exit /b 2
)

REM 问题 #12 A：校验 venv 有效性，无效则重建
if not exist "%PYTHON_EXE%" (
    echo [setup] 虚拟环境不存在或路径失效，重建中...
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [错误] 虚拟环境创建失败，请确认 python 已安装
        exit /b 3
    )
)

REM 问题 #12 B：确保 lark-oapi 已装
"%PYTHON_EXE%" -c "import lark_oapi" 2>nul
if errorlevel 1 (
    echo [setup] 安装 lark-oapi...
    "%PIP_EXE%" install -q lark-oapi
    if errorlevel 1 (
        echo [错误] lark-oapi 安装失败
        exit /b 4
    )
)

REM 检查是否已在运行
tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | find /I "lark_ws_listener" >nul
if not errorlevel 1 (
    echo [already running] 如需重启请: %0 restart
    exit /b 0
)

REM 启动（start /B 不弹窗）
start "NSKSDListener" /B "%PYTHON_EXE%" lark_ws_listener.py > "%LOG_FILE%" 2>&1
timeout /t 3 /nobreak >nul
echo [started] 凭证 APP_ID=%LARK_APP_ID:~0,8%**** 已注入
echo [log]     %LOG_FILE%
type "%LOG_FILE%"
exit /b 0

:stop
REM 按命令行匹配精准杀（避免误杀其他 python 进程）
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /V /FO LIST ^| findstr /I "lark_ws_listener"') do (
    taskkill /F /PID %%p 2>nul
)
wmic process where "name='python.exe' and commandline like '%%lark_ws_listener%%'" delete 2>nul | findstr /I "delete" >nul
echo [stopped]
exit /b 0

:restart
call :stop
timeout /t 1 /nobreak >nul
goto :start

:status
tasklist /FI "IMAGENAME eq python.exe" /V 2>nul | findstr /I "lark_ws_listener" >nul
if not errorlevel 1 (
    echo [running]
) else (
    echo [not running]
)
exit /b 0

:logs
if exist "%LOG_FILE%" (
    type "%LOG_FILE%"
) else (
    echo [无日志] %LOG_FILE% 不存在
)
exit /b 0
