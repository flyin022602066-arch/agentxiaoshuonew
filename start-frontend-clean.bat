@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
npm run dev -- --host 127.0.0.1 --port 5173