@echo off
chcp 65001 >nul
setlocal
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set NPM_CONFIG_UNICODE=true

REM ==========================================
REM Multi-Agent Novel System - Setup, Test and Start
REM ==========================================

echo ================================================================
echo Multi-Agent Novel System - Setup, Test and Start
echo ================================================================

echo.
echo [1/5] Installing Python dependencies...
cd /d "%~dp0"
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

echo.
echo [2/5] Running Python syntax check...
python -m py_compile backend\app\main.py
python -m py_compile backend\app\config.py
python -m py_compile backend\app\exceptions.py
python -m py_compile backend\app\utils\llm_client.py
python -m py_compile backend\app\agents\registry.py
python -m py_compile backend\app\memory\memory_engine.py
if errorlevel 1 (
    echo [ERROR] Syntax check failed
    pause
    exit /b 1
)
echo [OK] Syntax check passed

echo.
echo [3/5] Running backend smoke tests...
cd /d "%~dp0backend\tests"
python test_all.py
if errorlevel 1 (
    echo [ERROR] Tests failed
    pause
    exit /b 1
)
echo [OK] Smoke tests passed

echo.
echo [4/5] Starting backend server...
start "Novel Backend" cmd /k "chcp 65001>nul && set PYTHONIOENCODING=utf-8 && set PYTHONUTF8=1 && cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo.
echo [5/5] Starting frontend server...
start "Novel Frontend" cmd /k "chcp 65001>nul && set NPM_CONFIG_UNICODE=true && cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 5173"

echo.
echo ================================================================
echo [SUCCESS] Setup complete, tests passed, services are starting!
echo ================================================================
echo.
echo Open these URLs in your browser after the windows finish starting:
echo - Frontend: http://localhost:5173
echo - Backend Docs: http://localhost:8000/docs
echo - Health Check: http://localhost:8000/api/health
echo.
echo Notes:
echo - If a port is already occupied, close the old process first.
echo - Configure your LLM provider in the Project Config page.
echo.
pause
