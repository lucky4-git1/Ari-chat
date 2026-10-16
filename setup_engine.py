import os
import sys
import zipfile
import tarfile
import platform
import socket
import urllib.request
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

# llama.cpp release b11580 binaries across platforms
LLAMA_RELEASES = {
    "win_x64": "https://github.com/ggml-org/llama.cpp/releases/download/b11580/llama-b11580-bin-win-cpu-x64.zip",
    "linux_x64": "https://github.com/ggml-org/llama.cpp/releases/download/b11580/llama-b11580-bin-ubuntu-x64.zip",
    "macos_arm64": "https://github.com/ggml-org/llama.cpp/releases/download/b11580/llama-b11580-bin-macos-arm64.zip",
    "macos_x64": "https://github.com/ggml-org/llama.cpp/releases/download/b11580/llama-b11580-bin-macos-x64.zip",
}

# Hugging Face direct model download URLs
MODEL_URLS = {
    "ari_assistant_1.5b.gguf": "https://huggingface.co/sriyuth/ari-assistant-1.5b/resolve/main/ari_assistant_1.5b.gguf",
    "ari_assistant_3b.gguf": "https://huggingface.co/sriyuth/ari-assistant-3b/resolve/main/ari_assistant_3b.gguf",
}

def get_platform_key():
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "windows":
        return "win_x64"
    elif system == "darwin":
        if "arm" in machine or "aarch64" in machine:
            return "macos_arm64"
        return "macos_x64"
    elif system == "linux":
        return "linux_x64"
    return "linux_x64"

def get_local_ip():
    """Detects local LAN IP for seamless mobile/cross-device connectivity."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def download_with_progress(url: str, dest_path: Path, label: str = "Downloading"):
    """Downloads a file with an interactive command line progress indicator."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    
    req = urllib.request.Request(url, headers={"User-Agent": "AriChat-Installer/1.0"})
    with urllib.request.urlopen(req) as resp, open(temp_path, "wb") as out_file:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1 MB chunks
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = min(100, int(downloaded * 100 / total_size))
                mb_curr = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                sys.stdout.write(f"\r  -> {label}: {percent:3d}% [{mb_curr:6.1f}MB / {mb_total:6.1f}MB]")
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\r  -> {label}: {downloaded // (1024*1024)}MB downloaded")
                sys.stdout.flush()
    print()
    if temp_path.exists():
        if dest_path.exists():
            dest_path.unlink()
        temp_path.rename(dest_path)

def setup_binaries():
    """Ensures llama-server binary is present and executable for the current OS."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    is_win = platform.system().lower() == "windows"
    exe_name = "llama-server.exe" if is_win else "llama-server"
    server_exe = BIN_DIR / exe_name
    
    if server_exe.exists():
        if not is_win:
            try:
                server_exe.chmod(0o755)
            except Exception:
                pass
        print(f"[OK] Standalone llama-server engine found: {server_exe.name}")
        return True

    pkey = get_platform_key()
    url = LLAMA_RELEASES.get(pkey, LLAMA_RELEASES["linux_x64"])
    print(f"[*] llama-server binary not found for {pkey}. Downloading standalone portable engine...")
    zip_path = BIN_DIR / "llama_engine.zip"
    
    try:
        download_with_progress(url, zip_path, label=f"Engine [{pkey}]")
        print("[*] Extracting standalone engine...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(BIN_DIR)
        
        if zip_path.exists():
            zip_path.unlink()
            
        if not is_win and server_exe.exists():
            server_exe.chmod(0o755)
            
        print(f"[OK] Standalone engine installed successfully to: {BIN_DIR}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download standalone engine: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False

def setup_model(model_name: str = "ari_assistant_1.5b.gguf", auto_download: bool = True):
    """Ensures a specific model GGUF is available, checking local links or downloading if allowed."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = MODELS_DIR / model_name
    
    if target_path.exists() and target_path.stat().st_size > 100 * 1024 * 1024:
        mb = target_path.stat().st_size / (1024 * 1024)
        print(f"[OK] Local model ready: {model_name} ({mb:.1f} MB)")
        return True

    # Check common source locations in parent workspace
    potential_sources = [
        BASE_DIR.parent / "artifacts" / "checkpoints" / model_name,
        BASE_DIR.parent / model_name,
    ]
    for src in potential_sources:
        if src.exists() and src.stat().st_size > 100 * 1024 * 1024:
            print(f"[*] Found local model at {src}. Linking to {target_path}...")
            try:
                os.link(src, target_path)
                return True
            except Exception:
                try:
                    shutil.copyfile(src, target_path)
                    return True
                except Exception:
                    pass

    if auto_download and model_name in MODEL_URLS:
        url = MODEL_URLS[model_name]
        print(f"[*] Auto-downloading {model_name} from Hugging Face CDN...")
        try:
            download_with_progress(url, target_path, label=f"Model {model_name}")
            return True
        except Exception as e:
            print(f"[WARNING] Could not auto-download {model_name}: {e}")
            return False

    return False

def setup_models(require_3b: bool = False):
    """Ensures at least one primary model is ready (1.5B or 3B)."""
    ok_15b = setup_model("ari_assistant_1.5b.gguf", auto_download=True)
    ok_3b = setup_model("ari_assistant_3b.gguf", auto_download=require_3b)
    return ok_15b or ok_3b

def print_connectivity_banner(port: int = 8000):
    ip = get_local_ip()
    print("=" * 68)
    print("                     Ari Chat Application")
    print("            Private, Standalone AI (No Ollama Required)")
    print("=" * 68)
    print(f"  * Desktop Access (Local)    :  http://localhost:{port}")
    print(f"  * Mobile & Multi-Device LAN :  http://{ip}:{port}")
    print("    (Open on Android, iPhone, Mac, Linux, or iPad on same Wi-Fi)")
    print("=" * 68)

def main():
    print("=" * 68)
    print("         Ari Chat: Standalone Local Engine Verification")
    print("=" * 68)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    bin_ok = setup_binaries()
    models_ok = setup_models(require_3b=False)
    print("-" * 68)
    if bin_ok and models_ok:
        print("[SUCCESS] Zero-setup engine is ready! Everything runs 100% locally.")
        print_connectivity_banner()
    else:
        print("[INFO] Engine setup completed with warnings. Check logs above.")
    print("=" * 68)

if __name__ == "__main__":
    main()
