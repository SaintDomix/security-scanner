@echo off
setlocal
title SecureScanner
cd /d "%~dp0"

echo ================================================
echo   SecureScanner v2
echo ================================================
echo.

REM Check .venv exists
if not exist "backend\.venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first!
    echo.
    pause & exit /b 1
)

REM Check .env exists
if not exist "backend\.env" (
    echo [ERROR] backend\.env not found.
    echo Please run setup.bat first, then edit backend\.env
    echo.
    pause & exit /b 1
)

echo Starting backend (FastAPI)...
start "SecureScanner - Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Waiting for backend to start...
timeout /t 4 /nobreak >nul

echo Starting frontend (React / Vite)...
start "SecureScanner - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Waiting for frontend to start...
timeout /t 5 /nobreak >nul

echo Opening browser...
start http://localhost:5173

echo.
echo ================================================
echo   SecureScanner is running!
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Close the two terminal windows to stop.
echo ================================================
echo.
pause
