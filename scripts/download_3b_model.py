import os
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/resolve/main/qwen2.5-coder-3b-instruct-q4_k_m.gguf"
TARGET_FILE = MODELS_DIR / "qwen2.5-coder-3b-instruct-q4_k_m.gguf"

def download_3b():
    print("=" * 70)
    print("      Ari Chat: Download 3B GPT-Level Companion Model (Q4_K_M)")
    print("=" * 70)
    print(f"Target path: {TARGET_FILE}")
    
    if TARGET_FILE.exists():
        print(f"[OK] Model already exists ({TARGET_FILE.stat().st_size / (1024*1024):.1f} MB)!")
        return

    print("[*] Downloading Qwen 2.5 Coder 3B GGUF (~1.96 GB)...")
    print("    This model runs on low-end laptops (CPU-only, ~2.4 GB RAM) at ~15 tokens/sec.")
    print("    Press Ctrl+C to cancel at any time.\n")

    try:
        def reporthook(blocknum, blocksize, totalsize):
            if totalsize > 0:
                downloaded = blocknum * blocksize
                percent = min(100, int(downloaded * 100 / totalsize))
                mb_down = downloaded / (1024 * 1024)
                mb_total = totalsize / (1024 * 1024)
                sys.stdout.write(f"\r    Progress: {percent}% [{mb_down:.1f} MB / {mb_total:.1f} MB]")
                sys.stdout.flush()

        req = urllib.request.Request(MODEL_URL, headers={"User-Agent": "Ari-Chat/1.0"})
        with urllib.request.urlopen(req) as resp, open(TARGET_FILE, "wb") as f:
            total_size = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    mb_down = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    sys.stdout.write(f"\r    Progress: {percent}% [{mb_down:.1f} MB / {mb_total:.1f} MB]")
                    sys.stdout.flush()

        print("\n\n[SUCCESS] 3B Model installed successfully!")
        print("To run with this model, select it in the model dropdown or update DEFAULT_MODEL.")
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        if TARGET_FILE.exists():
            TARGET_FILE.unlink()

if __name__ == "__main__":
    download_3b()
