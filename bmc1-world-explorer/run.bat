@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo        BMC1 World Explorer (Minecraft 1.16.5)
echo ========================================================
echo.

cd /d "%~dp0"

REM Check for python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found on your system PATH.
    echo Please install Python 3.12+ from python.org and try again.
    pause
    exit /b 1
)

echo [1/3] Checking environment...
if not exist ".venv" (
    echo Creating virtual environment in .venv...
    python -m venv .venv
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo [2/3] Verifying dependencies...
python -m pip install -q -r requirements.txt

echo [3/3] Starting BMC1 World Explorer server...
echo.
echo Server running at: http://127.0.0.1:8000
echo.
echo Opening browser...
start http://127.0.0.1:8000

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
