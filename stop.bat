@echo off
echo ============================================
echo   Sea Tracker - Stopping...
echo ============================================
echo.

:: Kill Uvicorn
taskkill /F /FI "WINDOWTITLE eq Sea Tracker Backend" >nul 2>nul
taskkill /F /IM uvicorn.exe >nul 2>nul

:: Kill Celery
taskkill /F /FI "WINDOWTITLE eq Sea Tracker Celery*" >nul 2>nul
taskkill /F /IM celery.exe >nul 2>nul

:: Kill Vite
taskkill /F /FI "WINDOWTITLE eq Sea Tracker Frontend" >nul 2>nul

echo All Sea Tracker processes stopped.
pause
