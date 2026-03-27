@echo off
setlocal
title SecureScanner Setup
cd /d "%~dp0"

echo ================================================
echo   SecureScanner v2 - Setup
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH.
    echo Download from: https://www.python.org/downloads/
    echo IMPORTANT: Check "Add Python to PATH" during install!
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i

REM Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found in PATH.
    echo Download from: https://nodejs.org/ (LTS version)
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo [OK] Node %%i

echo.
echo [Step 1/4] Creating Python virtual environment...
cd backend

if not exist ".venv" (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause & exit /b 1
    )
    echo     Created .venv
) else (
    echo     .venv already exists, skipping.
)

echo.
echo [Step 2/4] Installing Python packages...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed. Check your internet connection.
    pause & exit /b 1
)
echo [OK] Python packages installed.

echo.
echo [Step 3/4] Creating .env config file...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [OK] Created backend\.env
    echo.
    echo *** IMPORTANT: Open backend\.env and change SECRET_KEY ***
    echo     Example: SECRET_KEY=mysupersecretkey123changethis456
) else (
    echo [OK] backend\.env already exists.
)

REM Create needed folders
if not exist "reports"      mkdir reports
if not exist "repositories" mkdir repositories

cd ..

echo.
echo [Step 4/4] Installing frontend packages...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] npm install failed.
    pause & exit /b 1
)
cd ..

echo.
echo ================================================
echo   Setup complete!
echo.
echo   Next steps:
echo   1. Edit backend\.env and set SECRET_KEY
echo   2. Double-click start.bat to run the app
echo   3. Open http://localhost:5173 in your browser
echo ================================================
echo.
pause
