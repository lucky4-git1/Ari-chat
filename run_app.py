import os
import sys
import time
import socket
import webbrowser
import threading
import subprocess
import signal
from pathlib import Path

# Ensure application root is in python path
APP_ROOT = Path(__file__).resolve().parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from setup_engine import setup_binaries, setup_models, get_local_ip, print_connectivity_banner
from app.services.engine_service import start_standalone_engine, stop_standalone_engine

def open_browser(url: str, delay: float = 1.8):
    """Opens browser after server has started listening."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[INFO] Open {url} in your browser ({e})")

def handle_shutdown(signum, frame):
    print("\n[*] Stopping Ari Chat services...")
    stop_standalone_engine()
    sys.exit(0)

def main():
    print("=" * 68)
    print("               ARI CHAT — STANDALONE AI COMPANION")
    print("              Zero Setup • Private • Embedded Engine")
    print("=" * 68)
    
    # 1. Verify engine binary & model
    setup_binaries()
    setup_models(require_3b=False)
    
    # 2. Start standalone llama engine
    print("[*] Launching embedded neural engine...")
    engine_started = start_standalone_engine()
    if engine_started:
        print("[OK] Embedded engine online!")
    else:
        print("[WARNING] Engine startup returned false, falling back to on-demand init.")

    # 3. Setup shutdown traps
    signal.signal(signal.SIGINT, handle_shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)

    # 4. Display cross-device connectivity banner
    port = 8000
    print_connectivity_banner(port=port)

    # 5. Launch browser automatically in background thread
    threading.Thread(target=open_browser, args=(f"http://localhost:{port}",), daemon=True).start()

    # 6. Run FastAPI application
    import uvicorn
    try:
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info", access_log=False)
    finally:
        stop_standalone_engine()

if __name__ == "__main__":
    main()
