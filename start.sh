#!/usr/bin/env bash
set -e

echo "======================================================================="
echo "         Ari Chat: Standalone AI Companion (Zero-Setup)"
echo "                   Powered by Ari-LLM 1.5B"
echo "======================================================================="
echo ""

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "[1/3] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

echo "[2/3] Checking dependencies..."
python3 -c "import fastapi, uvicorn, sqlalchemy, httpx, ddgs" 2>/dev/null || {
    echo "Installing required packages from requirements.txt..."
    pip3 install -r requirements.txt
}

echo "[3/3] Verifying standalone engine and model..."
python3 setup_engine.py

echo ""
echo "======================================================================="
echo "  Ari Chat running on: http://localhost:8000"
echo "  Press Ctrl+C to stop the application."
echo "======================================================================="
echo ""

# Try opening default browser
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:8000" &
elif command -v open &> /dev/null; then
    open "http://localhost:8000" &
fi

python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
