@echo off
title Ari Chat - Powered by Ari-LLM 1.5B
cls
echo =======================================================================
echo          Ari Chat: Production ChatGPT-Style Web Platform
echo                    Powered by Ari-LLM 1.5B
echo =======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python installation...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    pause
    exit /b 1
)

echo [2/3] Checking dependencies...
python -c "import fastapi, uvicorn, sqlalchemy, httpx, ddgs" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing required packages from requirements.txt...
    pip install -r requirements.txt
)

echo [3/3] Checking Ollama service status...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Ollama does not seem to be running on http://localhost:11434.
    echo Please make sure Ollama is started with model 'ari-assistant'.
    echo Continuing anyway...
)

echo.
echo =======================================================================
echo   Server starting on: http://localhost:8000
echo   Open your browser and navigate to: http://localhost:8000
echo   Press Ctrl+C to stop the server at any time.
echo =======================================================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
