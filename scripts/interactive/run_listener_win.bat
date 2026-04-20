@echo off
REM 日生研内容创作 · Windows 启动飞书长连接监听器
REM 用法:run_listener_win.bat [start|stop|status]

cd /d "%~dp0"
set VENV_DIR=.venv
set LOG_FILE=listener.out

if "%1"=="" set ACTION=start
if not "%1"=="" set ACTION=%1

if "%ACTION%"=="start" goto :start
if "%ACTION%"=="stop" goto :stop
if "%ACTION%"=="status" goto :status
echo 用法: %0 [start^|stop^|status]
exit /b 1

:start
if not exist "%VENV_DIR%" (
    echo [setup] Creating venv...
    python -m venv %VENV_DIR%
    "%VENV_DIR%\Scripts\pip.exe" install -q lark-oapi
)
tasklist /FI "IMAGENAME eq python.exe" /V | find "lark_ws_listener" >nul
if %ERRORLEVEL%==0 (
    echo [already running]
    exit /b 0
)
start /B "" "%VENV_DIR%\Scripts\python.exe" lark_ws_listener.py > %LOG_FILE% 2>&1
timeout /t 3 /nobreak >nul
echo [started] check %LOG_FILE%
type %LOG_FILE%
exit /b 0

:stop
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *lark_ws_listener*" 2>nul
wmic process where "name='python.exe' and commandline like '%%lark_ws_listener%%'" delete 2>nul
echo [stopped]
exit /b 0

:status
tasklist /FI "IMAGENAME eq python.exe" /V | find "lark_ws_listener"
if %ERRORLEVEL%==0 (echo [running]) else (echo [not running])
exit /b 0
