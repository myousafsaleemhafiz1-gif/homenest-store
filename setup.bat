@echo off
setlocal
cd /d %~dp0
echo ========================================
echo       HomeNest Store - Setup
echo ========================================
where py >nul 2>&1
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ and run this file again.
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating virtual environment...
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy /y .env.example .env >nul
echo.
echo Setup complete.
echo Start the store with run.bat
pause
