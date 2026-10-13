#!/usr/bin/env bash
# =======================================================================
#          Ari Chat: Production ChatGPT-Style Web Platform
#                    Powered by Ari-LLM 1.5B
# =======================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================="
echo "         Ari Chat: Production ChatGPT-Style Web Platform"
echo "                   Powered by Ari-LLM 1.5B"
echo "======================================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.9+."
    exit 1
fi

# Check / Install Dependencies
echo "[1/3] Checking dependencies..."
python3 -c "import fastapi, uvicorn, sqlalchemy, httpx, ddgs" &> /dev/null || {
    echo "Installing requirements..."
    pip3 install -r requirements.txt
}

# Check Ollama
echo "[2/3] Checking Ollama service..."
curl -s http://localhost:11434/api/tags > /dev/null 2>&1 || {
    echo "[WARNING] Ollama is not detected at http://localhost:11434."
    echo "Make sure Ollama is running: 'ollama run ari-assistant'"
}

echo "[3/3] Starting Ari Chat Server on http://localhost:8000 ..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
