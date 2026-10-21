import os
import sys
import shutil
import zipfile
import subprocess
import json
import urllib.request
import urllib.error
from pathlib import Path

APP_DIR = Path("e:/Ari-llm-source/ari-chat-app").resolve()
DIST_DIR = APP_DIR / "dist"
RELEASE_DIR = APP_DIR / "release_packages"
RELEASE_DIR.mkdir(parents=True, exist_ok=True)

def get_github_token() -> str:
    """Retrieves GitHub token from git credential manager."""
    try:
        p = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(APP_DIR)
        )
        out, _ = p.communicate(input="protocol=https\nhost=github.com\n\n")
        for line in out.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"[!] Error fetching git credential: {e}")
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token
    raise RuntimeError("Could not find GitHub token from git credentials or environment!")

def build_windows_installer() -> Path:
    """Compiles AriChat-Setup-v1.0.1.exe using Inno Setup Compiler (ISCC.exe) if not already built."""
    installer_path = RELEASE_DIR / "AriChat-Setup-v1.0.1.exe"
    if installer_path.exists() and installer_path.stat().st_size > 500 * 1024 * 1024:
        print(f"[i] Using existing Windows Installer: {installer_path.name} ({installer_path.stat().st_size / (1024*1024):.1f} MB)")
        return installer_path

    iscc_candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
    ]
    iscc_exe = next((p for p in iscc_candidates if p.exists()), None)
    if not iscc_exe:
        raise FileNotFoundError("Inno Setup Compiler (ISCC.exe) not found!")

    # Make sure AriChat.exe exists in APP_DIR root
    dist_exe = DIST_DIR / "AriChat.exe"
    root_exe = APP_DIR / "AriChat.exe"
    if dist_exe.exists():
        shutil.copy2(dist_exe, root_exe)

    iss_file = APP_DIR / "installer" / "AriChat.iss"
    print(f"[*] Compiling Windows installer using Inno Setup ({iscc_exe})...")
    subprocess.run([str(iscc_exe), str(iss_file)], check=True, cwd=str(APP_DIR))
    
    installer_path = RELEASE_DIR / "AriChat-Setup-v1.0.1.exe"
    if not installer_path.exists():
        raise FileNotFoundError(f"Installer not found at {installer_path}")
    
    print(f"[OK] Successfully compiled Windows Installer: {installer_path.name} ({installer_path.stat().st_size / (1024*1024):.1f} MB)")
    return installer_path

def create_windows_package():
    """Packages complete standalone Windows zip release with pre-installed Ari-1.5B model & embedded engine."""
    zip_path = RELEASE_DIR / "AriChat-v1.0.1-Windows.zip"
    print(f"[*] Creating {zip_path.name}...")
    
    exe_path = DIST_DIR / "AriChat.exe"
    if not exe_path.exists():
        exe_path = APP_DIR / "AriChat.exe"
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        if exe_path.exists():
            print(f" -> Adding AriChat.exe ({exe_path.stat().st_size / (1024*1024):.1f} MB)")
            zf.write(exe_path, arcname="AriChat/AriChat.exe")
        
        for fname in ["start.bat", "run_app.py", "setup_engine.py", "requirements.txt", "README.md", "app.ico"]:
            fpath = APP_DIR / fname
            if fpath.exists():
                zf.write(fpath, arcname=f"AriChat/{fname}")
        
        bin_dir = APP_DIR / "bin"
        if bin_dir.exists():
            for root, _, files in os.walk(bin_dir):
                for f in files:
                    fp = Path(root) / f
                    arc = f"AriChat/bin/{fp.relative_to(bin_dir)}"
                    zf.write(fp, arcname=arc)
        
        app_dir = APP_DIR / "app"
        if app_dir.exists():
            for root, _, files in os.walk(app_dir):
                for f in files:
                    if "__pycache__" in root or f.endswith(".pyc"):
                        continue
                    fp = Path(root) / f
                    arc = f"AriChat/app/{fp.relative_to(app_dir)}"
                    zf.write(fp, arcname=arc)

        static_dir = APP_DIR / "static"
        if static_dir.exists():
            for root, _, files in os.walk(static_dir):
                for f in files:
                    fp = Path(root) / f
                    arc = f"AriChat/static/{fp.relative_to(static_dir)}"
                    zf.write(fp, arcname=arc)

        m15 = APP_DIR / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
        if not m15.exists():
            m15 = APP_DIR / "models" / "ari_assistant_1.5b.gguf"
        if m15.exists():
            print(f" -> Adding pre-installed model: {m15.name} ({m15.stat().st_size / (1024*1024):.1f} MB)")
            zf.write(m15, arcname=f"AriChat/models/{m15.name}")

    print(f"[OK] Created {zip_path.name} ({zip_path.stat().st_size / (1024*1024):.1f} MB)")
    return zip_path

def create_crossplatform_package():
    """Packages lightweight universal package for macOS, Linux, and Android."""
    zip_path = RELEASE_DIR / "AriChat-v1.0.1-CrossPlatform.zip"
    print(f"[*] Creating {zip_path.name}...")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in ["start.sh", "start-android.sh", "run_app.py", "setup_engine.py", "requirements.txt", "README.md", "app.ico"]:
            fpath = APP_DIR / fname
            if fpath.exists():
                zf.write(fpath, arcname=f"AriChat/{fname}")
        
        app_dir = APP_DIR / "app"
        if app_dir.exists():
            for root, _, files in os.walk(app_dir):
                for f in files:
                    if "__pycache__" in root or f.endswith(".pyc"):
                        continue
                    fp = Path(root) / f
                    arc = f"AriChat/app/{fp.relative_to(app_dir)}"
                    zf.write(fp, arcname=arc)

        static_dir = APP_DIR / "static"
        if static_dir.exists():
            for root, _, files in os.walk(static_dir):
                for f in files:
                    fp = Path(root) / f
                    arc = f"AriChat/static/{fp.relative_to(static_dir)}"
                    zf.write(fp, arcname=arc)

    print(f"[OK] Created {zip_path.name} ({zip_path.stat().st_size / (1024*1024):.1f} MB)")
    return zip_path

def github_api_request(url: str, token: str, method: str = "GET", data: bytes = None, content_type: str = "application/json"):
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AriChat-Release-Agent",
            "Content-Type": content_type
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[!] GitHub API HTTP {e.code} Error on {url}: {err_body}")
        raise

def upload_release_asset(upload_url_template: str, token: str, file_path: Path):
    """Uploads an asset to a GitHub release."""
    upload_url = upload_url_template.split("{")[0] + f"?name={file_path.name}"
    print(f"[*] Uploading {file_path.name} ({file_path.stat().st_size / (1024*1024):.1f} MB) to GitHub Release...")
    
    file_size = file_path.stat().st_size
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    content_type = "application/x-msdownload" if file_path.suffix == ".exe" else "application/zip"
    
    req = urllib.request.Request(
        upload_url,
        data=file_bytes,
        method="POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AriChat-Release-Agent",
            "Content-Type": content_type,
            "Content-Length": str(file_size)
        }
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[OK] Uploaded {file_path.name}! Download URL: {res.get('browser_download_url')}")
        return res

def publish_release(repo: str = "lucky4-git1/Ari-chat", tag: str = "v1.0.1"):
    token = get_github_token()
    print(f"[*] Authenticated with GitHub for repo {repo}")
    
    # 1. Build installer and zip packages
    installer_exe = build_windows_installer()
    win_zip = create_windows_package()
    cross_zip = create_crossplatform_package()
    
    # 2. Check if release already exists
    release_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    existing_release = None
    try:
        existing_release = github_api_request(release_url, token)
        print(f"[i] Found existing release for tag {tag} (ID: {existing_release['id']})")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    release_body = """# Ari Chat Application v1.0.1 — Standalone AI Companion

A production-ready, zero-setup, fully offline AI assistant powered natively by **Ari-1.5B** and **Ari-3B**.

### ✨ What's New in v1.0.1
- 🚀 **Generation Stability Fix:** Fixed premature token stream truncation and resolved HTTP 503 engine weight warmup handling. Offline chatting streams reliably and cleanly without cuts.
- 🔄 **In-App Auto-Updater:** Ari Chat now automatically checks for new updates on launch. When a new version is released, an update banner appears with one-click download & background installer upgrade without having to manually hunt on GitHub!
- 🧠 **Autonomous Long-Term Memory:** Ari now autonomously extracts user preferences, technical stacks, names, and explicit instructions straight from conversation turns and injects relevant context into future chats.
- 📥 **Dedicated Ari 3B Model Puller:** Prominent "Pull Ari 3B" button added directly into the top navigation bar and model switcher. Downloads Ari 3B (1.93 GB) with real-time speed, bytes progress, and automatic registration.
- 🛠️ **Multi-Path Model Discovery:** Models in user directory, application install root (`%LOCALAPPDATA%\\Programs\\AriChat\\models`), or portable folders are automatically discovered and shared.

---

### 📦 Downloads & Installers

| Package | Platform | Type | Details |
| :--- | :--- | :--- | :--- |
| **`AriChat-Setup-v1.0.1.exe`** | Windows 10/11 (x64) | **Windows Installer** | **Recommended:** Complete Setup Wizard with Desktop shortcut, Start Menu entry, embedded llama engine, and pre-installed `ari_assistant_1.5b.gguf`. |
| **`AriChat-v1.0.1-Windows.zip`** | Windows 10/11 (x64) | **Portable Archive** | Extract anywhere and run `AriChat.exe` or `start.bat` without installation. |
| **`AriChat-v1.0.1-CrossPlatform.zip`** | macOS, Linux, Android | **Universal Package** | Run `./start.sh` or `./start-android.sh`. Automatically fetches platform binaries and models. |

---

### 🧠 Standalone GGUF Models (Hugging Face)
You can pull **Ari 3B** directly from inside the Ari Chat application, or download manually:
- **Ari 1.5B Assistant (Q4_K_M, 986 MB):** [Download ari_assistant_1.5b.gguf](https://huggingface.co/sriyuth/ari-assistant-1.5b/resolve/main/ari_assistant_1.5b.gguf)
- **Ari 3B Assistant (Q4_K_M, 1.93 GB):** [Download ari_assistant_3b.gguf](https://huggingface.co/sriyuth/ari-assistant-3b/resolve/main/ari_assistant_3b.gguf)

---

### 🚀 Getting Started

#### Windows (Installer Wizard)
1. Download and run **`AriChat-Setup-v1.0.1.exe`**.
2. Follow the setup wizard and launch **Ari Chat** from your Desktop or Start Menu!

#### macOS / Linux
1. Download and extract **`AriChat-v1.0.1-CrossPlatform.zip`**.
2. Run in terminal:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

#### Android (Native On-Device via Termux)
1. Install [Termux](https://termux.dev).
2. Download or git clone the repo into Termux.
3. Run:
   ```bash
   chmod +x start-android.sh
   ./start-android.sh
   ```
4. Open Chrome on Android and visit `http://127.0.0.1:8000`.

#### Mobile LAN Access (Any Phone/Tablet)
When Ari Chat starts on your PC, it displays your local Wi-Fi address:
```
📱 Connect any mobile / tablet on your Wi-Fi at:
   http://192.168.x.x:8000
```
Open that URL in your mobile browser to chat privately with your local Ari LLM!
"""

    if not existing_release:
        print("[*] Creating new GitHub release...")
        create_payload = {
            "tag_name": tag,
            "target_commitish": "main",
            "name": "Ari Chat Application v1.0.1 — Standalone AI Companion",
            "body": release_body,
            "draft": False,
            "prerelease": False
        }
        rel = github_api_request(
            f"https://api.github.com/repos/{repo}/releases",
            token,
            method="POST",
            data=json.dumps(create_payload).encode("utf-8")
        )
    else:
        rel = existing_release
        github_api_request(
            f"https://api.github.com/repos/{repo}/releases/{rel['id']}",
            token,
            method="PATCH",
            data=json.dumps({"body": release_body}).encode("utf-8")
        )

    upload_url = rel["upload_url"]
    
    # Check existing assets to avoid 422 duplicate error
    existing_assets = {a["name"]: a["id"] for a in rel.get("assets", [])}
    
    for pkg in [installer_exe, win_zip, cross_zip]:
        if pkg.name in existing_assets:
            print(f"[i] Replacing existing release asset {pkg.name} (ID: {existing_assets[pkg.name]})...")
            del_req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/releases/assets/{existing_assets[pkg.name]}",
                method="DELETE",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "AriChat-Release-Agent"
                }
            )
            with urllib.request.urlopen(del_req) as d_resp:
                pass
        
        upload_release_asset(upload_url, token, pkg)

    print("\n=======================================================")
    print(" [OK] GITHUB RELEASE UPDATED & ASSETS UPLOADED!")
    print(f" URL: {rel.get('html_url')}")
    print("=======================================================\n")

if __name__ == "__main__":
    publish_release()
