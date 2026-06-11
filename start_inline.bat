@echo off
set PYTHONIOENCODING=utf-8
echo ============================================
echo   Sea Tracker - Starting Inline
echo   (Press Ctrl+C to stop everything)
echo ============================================
echo.

npx concurrently -n "FastAPI,Celery,Beat,Vite" -c "blue,green,magenta,yellow" "cd backend && call venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload" "cd backend && call venv\Scripts\activate.bat && celery -A tasks.celery_app worker --pool=solo -l info" "cd backend && call venv\Scripts\activate.bat && celery -A tasks.celery_app beat -l info" "cd frontend && npm run dev"
