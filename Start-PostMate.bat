@echo off
setlocal EnableExtensions DisableDelayedExpansion

if /i "%~1"=="--backend" goto backend
if /i "%~1"=="--frontend" goto frontend
if not "%~1"=="" if /i not "%~1"=="--check" goto usage

title PostMate Launcher
echo.
echo   PostMate - Local Application Launcher
echo   ====================================
echo.

if not exist "%~dp0backend\.venv\Scripts\python.exe" (
    echo ERROR: Backend virtual environment was not found.
    echo Follow the Python setup instructions in README.md first.
    goto failure
)
if not exist "%~dp0backend\.env" (
    echo ERROR: backend\.env was not found.
    echo Configure the backend environment using README.md first.
    goto failure
)
where node.exe >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js was not found. Install Node.js 22 LTS first.
    goto failure
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm was not found. Install Node.js with npm first.
    goto failure
)
if not exist "%~dp0frontend\node_modules\vite\bin\vite.js" (
    echo ERROR: Frontend dependencies are missing.
    echo Run npm ci from the frontend folder, then try again.
    goto failure
)
"%~dp0backend\.venv\Scripts\python.exe" -c "import uvicorn, psycopg" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Backend dependencies are missing.
    echo Install backend\requirements.lock.txt into the backend virtual environment.
    goto failure
)

if /i "%~1"=="--check" (
    echo Startup requirements are available.
    exit /b 0
)

rem Reuse ports already running so a second double-click does not start duplicates.
"%~dp0backend\.venv\Scripts\python.exe" -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(s.connect_ex(('127.0.0.1',8000)))" >nul 2>&1
if errorlevel 1 (
    echo Starting backend on port 8000...
    start "PostMate Backend" "%ComSpec%" /d /k ""%~f0" --backend"
) else (
    echo Port 8000 is already running; keeping the existing backend.
)

"%~dp0backend\.venv\Scripts\python.exe" -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(s.connect_ex(('127.0.0.1',5173)))" >nul 2>&1
if errorlevel 1 (
    echo Starting frontend on port 5173...
    start "PostMate Frontend" "%ComSpec%" /d /k ""%~f0" --frontend"
) else (
    echo Port 5173 is already running; keeping the existing frontend.
    start "" "http://localhost:5173/"
)

echo.
echo Application: http://localhost:5173/
echo API docs:    http://127.0.0.1:8000/docs
echo.
echo Keep the server windows open while using PostMate.
echo To stop a server, press Ctrl+C in its window.
echo PostgreSQL must be running for the backend to connect.
echo.
timeout /t 5 >nul
exit /b 0

:backend
title PostMate Backend
cd /d "%~dp0backend"
"%~dp0backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
exit /b %errorlevel%

:frontend
title PostMate Frontend
cd /d "%~dp0frontend"
call npm.cmd run dev -- --port 5173 --strictPort --open
exit /b %errorlevel%

:failure
echo.
if /i "%~1"=="--check" exit /b 1
pause
exit /b 1

:usage
echo Usage: Start-PostMate.bat [--check]
exit /b 1
