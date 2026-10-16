#!/usr/bin/env bash
# =======================================================================
#               Ari Chat — Android & Termux Native Launcher
# =======================================================================

echo "======================================================================="
echo "               Ari Chat for Android (Termux Environment)"
echo "======================================================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Check if running in Termux
if [ -d "$PREFIX" ] && [ -x "$PREFIX/bin/pkg" ]; then
    echo "[*] Termux environment detected."
    echo "[1/3] Ensuring required packages (python, clang, cmake, llama.cpp)..."
    pkg update -y || true
    pkg install -y python clang cmake git || true
    
    # Try installing llama.cpp package if available in Termux repo
    pkg install -y llama.cpp 2>/dev/null || true
fi

echo "[2/3] Checking Python dependencies..."
pip install -r requirements.txt || pip3 install -r requirements.txt

echo "[3/3] Starting Ari Chat Server on 0.0.0.0:8000..."
python3 run_app.py
