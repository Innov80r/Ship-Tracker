@echo off
echo ============================================
echo   Sea Tracker - Starting...
echo ============================================
echo.

:: Start Redis (if using Memurai or Redis Windows)
echo [1/4] Checking Redis...
redis-cli ping >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Redis not running. Start Redis/Memurai first.
)

:: Start Backend
echo [2/4] Starting Backend (FastAPI)...
start "Sea Tracker Backend" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment for backend
timeout /t 3 /nobreak >nul

:: Start Celery Worker
echo [3/4] Starting Celery Worker...
start "Sea Tracker Celery" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && celery -A tasks.celery_app worker --pool=solo --loglevel=info"

:: Start Celery Beat
start "Sea Tracker Celery Beat" cmd /k "cd /d %~dp0backend && call venv\Scripts\activate.bat && celery -A tasks.celery_app beat --loglevel=info"

:: Start Frontend
echo [4/4] Starting Frontend (Vite)...
start "Sea Tracker Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   Sea Tracker is starting!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.
pause
