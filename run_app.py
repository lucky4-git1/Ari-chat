import os
import sys
import time
import socket
import webbrowser
import threading
import subprocess
import signal
import shutil
import argparse
from pathlib import Path
from typing import Optional

# 1. Ensure stdout/stderr redirection when running without console (console=False)
if sys.stdout is None or sys.stderr is None:
    try:
        log_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "AriChat" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / "arichat.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = log_file
        if sys.stderr is None:
            sys.stderr = log_file
    except Exception:
        pass

# 2. Ensure application root is in python path
if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
else:
    APP_ROOT = Path(__file__).resolve().parent

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from setup_engine import setup_binaries, setup_models, get_local_ip, print_connectivity_banner
from app.services.engine_service import start_standalone_engine, stop_standalone_engine

def find_app_browser() -> Optional[str]:
    """Finds an installed browser that supports --app standalone window mode (Edge, Chrome, Brave, Chromium)."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        candidates = [
            os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(program_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join(program_files_x86, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    else:  # Linux / Unix
        for binary in [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
            "microsoft-edge-stable",
            "brave-browser",
        ]:
            path = shutil.which(binary)
            if path:
                return path
    return None

def get_app_profile_dir() -> Path:
    """Returns dedicated profile directory for the desktop window sandbox."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    profile_dir = base / "AriChat" / "app_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    return profile_dir

def wait_for_server(port: int = 8000, timeout: float = 15.0) -> bool:
    """Polls server health until it responds."""
    import urllib.request
    start = time.time()
    url = f"http://127.0.0.1:{port}/api/health"
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.8) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False

def is_server_already_running(port: int = 8000) -> bool:
    """Checks if Ari Chat is already listening and healthy on port."""
    import urllib.request
    try:
        url = f"http://127.0.0.1:{port}/api/health"
        with urllib.request.urlopen(url, timeout=0.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def launch_desktop_window(port: int = 8000, prefer_browser_tab: bool = False) -> Optional[subprocess.Popen]:
    """Launches the dedicated standalone desktop app window (or browser tab if requested/fallback)."""
    url = f"http://127.0.0.1:{port}"
    if prefer_browser_tab:
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[INFO] Open {url} in your browser ({e})")
        return None

    browser = find_app_browser()
    if browser:
        profile_dir = get_app_profile_dir()
        args = [
            browser,
            f"--app={url}",
            "--window-size=1280,860",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-sync",
            "--disable-features=Translate",
            "--app-id=AriChat",
        ]
        try:
            proc = subprocess.Popen(args)
            return proc
        except Exception as e:
            print(f"[WARNING] Could not launch native app window ({e}). Falling back to browser tab.")

    # Fallback to default browser
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[INFO] Open {url} in your browser ({e})")
    return None

def main():
    parser = argparse.ArgumentParser(description="Ari Chat Desktop Application")
    parser.add_argument("--port", type=int, default=8000, help="Port to run FastAPI server on")
    parser.add_argument("--headless", action="store_true", help="Run server only without opening window")
    parser.add_argument("--server-only", action="store_true", help="Run server only without opening window")
    parser.add_argument("--browser", action="store_true", help="Open in default browser tab instead of app window")
    args, _ = parser.parse_known_args()

    port = args.port
    is_headless = args.headless or args.server_only
    prefer_browser = args.browser

    # Check if Ari Chat is already running on port
    if is_server_already_running(port):
        print(f"[*] Ari Chat is already running on port {port}. Launching application window...")
        if not is_headless:
            window_proc = launch_desktop_window(port=port, prefer_browser_tab=prefer_browser)
            if window_proc:
                window_proc.wait()
        return

    print("=" * 68)
    print("               ARI CHAT — STANDALONE AI COMPANION")
    print("              Zero Setup • Private • Embedded Engine")
    print("=" * 68)

    # 1. Verify engine binary & model (checks local installed directories first, no re-download)
    setup_binaries()
    setup_models(require_3b=False)

    # 2. Start standalone llama engine
    print("[*] Launching embedded neural engine...")
    engine_started = start_standalone_engine()
    if engine_started:
        print("[OK] Embedded engine online!")
    else:
        print("[WARNING] Engine startup returned false, falling back to on-demand init.")

    # 3. Setup uvicorn server in a separate thread
    import uvicorn
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config=config)

    def run_server():
        server.run()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 4. Wait for server to become responsive
    server_up = wait_for_server(port=port, timeout=15.0)
    if not server_up:
        print(f"[WARNING] Server did not report healthy within timeout, continuing...")

    # 5. Display cross-device connectivity banner
    print_connectivity_banner(port=port)

    # 6. Setup shutdown handler
    def shutdown_all(*_):
        print("\n[*] Stopping Ari Chat services...")
        server.should_exit = True
        stop_standalone_engine()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_all)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown_all)

    # 7. Launch desktop application window
    if not is_headless:
        print("[*] Opening Ari Chat desktop application window...")
        window_proc = launch_desktop_window(port=port, prefer_browser_tab=prefer_browser)
        if window_proc:
            # Wait until user closes the application window
            try:
                window_proc.wait()
            except KeyboardInterrupt:
                pass
            print("[*] Application window closed by user. Shutting down...")
            shutdown_all()
            return

    # If headless or browser fallback, keep main thread alive
    try:
        while server_thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown_all()

if __name__ == "__main__":
    main()
