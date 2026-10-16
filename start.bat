@echo off
title Ari Chat - Standalone AI Companion
cls
echo =======================================================================
echo          Ari Chat: Standalone AI Companion (Zero-Setup)
echo                    Powered by Ari-LLM 1.5B & 3B
echo =======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ from python.org and try again.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
python -c "import fastapi, uvicorn, sqlalchemy, httpx, ddgs, pydantic" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing required packages from requirements.txt...
    pip install -r requirements.txt
)

echo [3/3] Starting Ari Chat...
python run_app.py
pause
