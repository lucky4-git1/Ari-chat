import os
import sys
import zipfile
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"

LLAMA_WINDOWS_CPU_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b11580/llama-b11580-bin-win-cpu-x64.zip"
DEFAULT_MODEL_NAME = "ari_assistant_1.5b.gguf"

def setup_binaries():
    """Ensures llama-server.exe is present in bin/ directory."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    server_exe = BIN_DIR / "llama-server.exe"
    
    if server_exe.exists():
        print(f"[OK] Standalone llama-server engine found: {server_exe}")
        return True

    print("[*] llama-server binary not found. Downloading standalone portable engine (~19.5 MB)...")
    zip_path = BIN_DIR / "llama_cpu.zip"
    try:
        def reporthook(blocknum, blocksize, totalsize):
            if totalsize > 0:
                percent = min(100, int(blocknum * blocksize * 100 / totalsize))
                sys.stdout.write(f"\r    Downloading: {percent}% [{blocknum * blocksize // (1024*1024)}MB / {totalsize // (1024*1024)}MB]")
                sys.stdout.flush()

        req = urllib.request.Request(LLAMA_WINDOWS_CPU_URL, headers={"User-Agent": "Ari-Chat-Setup/1.0"})
        with urllib.request.urlopen(req) as resp, open(zip_path, "wb") as out_file:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    sys.stdout.write(f"\r    Downloading: {percent}% [{downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB]")
                    sys.stdout.flush()
        print("\n[*] Extracting standalone engine...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(BIN_DIR)
        
        if zip_path.exists():
            zip_path.unlink()
        
        print(f"[OK] Standalone engine installed successfully to: {BIN_DIR}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to download standalone engine: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False

def setup_model():
    """Ensures the Ari GGUF model exists in models/ directory."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target_model = MODELS_DIR / DEFAULT_MODEL_NAME
    
    if target_model.exists():
        print(f"[OK] Local model found: {target_model} ({target_model.stat().st_size / (1024*1024):.1f} MB)")
        return True

    # Check common source locations in workspace
    potential_sources = [
        BASE_DIR.parent / "artifacts" / "checkpoints" / DEFAULT_MODEL_NAME,
        BASE_DIR.parent / "artifacts" / "checkpoints" / "ari_assistant_1.5b.gguf",
        BASE_DIR.parent / DEFAULT_MODEL_NAME,
    ]

    for src in potential_sources:
        if src.exists():
            print(f"[*] Found model at {src}. Linking to {target_model}...")
            try:
                os.link(src, target_model)
                print(f"[OK] Hardlink created successfully ({target_model.stat().st_size / (1024*1024):.1f} MB).")
                return True
            except Exception:
                try:
                    import shutil
                    shutil.copyfile(src, target_model)
                    print(f"[OK] Model copied successfully.")
                    return True
                except Exception as ce:
                    print(f"[WARNING] Could not copy model: {ce}")

    print(f"[WARNING] Model file '{DEFAULT_MODEL_NAME}' not found in {MODELS_DIR}.")
    print("         Please ensure 'ari_assistant_1.5b.gguf' is placed in the 'models/' directory.")
    return False

def main():
    print("=" * 65)
    print("         Ari Chat: Standalone Local Engine Verification")
    print("=" * 65)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    bin_ok = setup_binaries()
    model_ok = setup_model()
    print("-" * 65)
    if bin_ok and model_ok:
        print("[SUCCESS] Zero-setup engine is ready! Everything runs 100% locally.")
    else:
        print("[INFO] Engine setup completed with warnings. Check logs above.")
    print("=" * 65)

if __name__ == "__main__":
    main()
