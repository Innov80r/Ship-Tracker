@echo off
echo ============================================
echo   Sea Tracker - Setup Script
echo ============================================
echo.

:: Check Python
python --version 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

:: Check Node
node --version 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install from nodejs.org
    pause
    exit /b 1
)

:: Python virtual environment
echo [1/5] Creating Python virtual environment...
if not exist backend\venv (
    cd backend
    python -m venv venv
    cd ..
)

:: Install Python dependencies
echo [2/5] Installing Python dependencies...
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if exist requirements-dev.txt (
    pip install -r requirements-dev.txt --quiet
)
cd ..

:: Install frontend dependencies
echo [3/5] Installing frontend dependencies...
cd frontend
call npm install
cd ..

:: Create directories
echo [4/5] Creating directories...
if not exist backend\static mkdir backend\static

:: Done
echo [5/5] Setup complete!
echo.
echo ============================================
echo   BEFORE STARTING:
echo   1. Install PostgreSQL and create database 'seatracker'
echo   2. Enable PostGIS:  CREATE EXTENSION postgis;
echo   3. Install Redis (or use Memurai for Windows)
echo   4. Edit backend\.env with your API keys
echo ============================================
echo.
pause
