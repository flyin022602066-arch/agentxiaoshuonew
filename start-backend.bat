@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
taskkill /F /IM python.exe 2>nul
cd /d "D:\new test\novel-agent-system\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
