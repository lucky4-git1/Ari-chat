import os
import sys
import time
import json
import logging
import threading
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import VERSION, DATA_DIR

logger = logging.getLogger(__name__)

REPO_OWNER_REPO = "lucky4-git1/Ari-chat"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{REPO_OWNER_REPO}/releases/latest"

UPDATES_DIR = DATA_DIR / "updates"
UPDATES_DIR.mkdir(parents=True, exist_ok=True)

class UpdaterService:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._download_state: Dict[str, Any] = {
            "status": "idle",  # idle, checking, downloading, ready_to_install, error, cancelled
            "current_version": VERSION,
            "latest_version": VERSION,
            "release_title": "",
            "release_notes": "",
            "download_url": "",
            "filename": "",
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "percent": 0.0,
            "speed_mbps": 0.0,
            "eta_seconds": 0,
            "message": "App is up to date"
        }

    def _parse_version(self, v_str: str) -> tuple:
        """Parses version strings like 'v1.0.1' or '1.0.0' into tuple of ints for accurate comparison."""
        v = v_str.strip().lstrip("vV")
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)

    def check_for_update(self) -> Dict[str, Any]:
        """Queries GitHub Releases API for the latest release and checks if a newer version is available."""
        try:
            req = urllib.request.Request(
                GITHUB_LATEST_RELEASE_API,
                headers={
                    "User-Agent": "AriChat-App/1.0",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                if resp.status != 200:
                    return {
                        "update_available": False,
                        "current_version": VERSION,
                        "message": f"GitHub API returned HTTP {resp.status}"
                    }
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            latest_v = tag_name.lstrip("vV")
            current_v = VERSION.lstrip("vV")

            is_newer = self._parse_version(latest_v) > self._parse_version(current_v)

            # Find suitable asset: preferred Windows installer
            download_url = ""
            filename = ""
            size_bytes = 0

            assets = data.get("assets", [])
            # Priority 1: Windows Installer (.exe)
            for a in assets:
                name = a.get("name", "")
                if name.endswith(".exe") and "Setup" in name:
                    download_url = a.get("browser_download_url", "")
                    filename = name
                    size_bytes = a.get("size", 0)
                    break

            # Priority 2: Windows zip
            if not download_url:
                for a in assets:
                    name = a.get("name", "")
                    if name.endswith(".zip") and "Windows" in name:
                        download_url = a.get("browser_download_url", "")
                        filename = name
                        size_bytes = a.get("size", 0)
                        break

            # Fallback: tarball or first asset
            if not download_url and assets:
                download_url = assets[0].get("browser_download_url", "")
                filename = assets[0].get("name", "")
                size_bytes = assets[0].get("size", 0)

            result = {
                "update_available": is_newer,
                "current_version": VERSION,
                "latest_version": latest_v,
                "release_title": data.get("name", f"Ari Chat v{latest_v}"),
                "release_notes": data.get("body", "Bug fixes and performance improvements."),
                "download_url": download_url,
                "filename": filename,
                "size_bytes": size_bytes,
                "published_at": data.get("published_at", "")
            }

            with self._lock:
                self._download_state.update({
                    "current_version": VERSION,
                    "latest_version": latest_v,
                    "release_title": result["release_title"],
                    "release_notes": result["release_notes"],
                    "download_url": download_url,
                    "filename": filename,
                    "total_bytes": size_bytes,
                    "message": "Update available!" if is_newer else "Ari Chat is up to date."
                })

            return result
        except Exception as e:
            logger.warning(f"Failed to check for updates: {e}")
            return {
                "update_available": False,
                "current_version": VERSION,
                "error": str(e),
                "message": "Could not contact update server."
            }

    def start_download(self) -> Dict[str, Any]:
        """Starts background download of the latest release installer/package."""
        with self._lock:
            if self._download_state["status"] == "downloading":
                return {"ok": False, "message": "Download already in progress."}

            url = self._download_state.get("download_url")
            filename = self._download_state.get("filename")
            if not url or not filename:
                # Run check first
                check = self.check_for_update()
                url = check.get("download_url")
                filename = check.get("filename")

            if not url or not filename:
                return {"ok": False, "message": "No update package available for download."}

            dest_path = UPDATES_DIR / filename
            self._stop_requested = False
            self._download_state.update({
                "status": "downloading",
                "bytes_downloaded": 0,
                "percent": 0.0,
                "speed_mbps": 0.0,
                "eta_seconds": 0,
                "message": f"Downloading {filename}..."
            })

            self._thread = threading.Thread(
                target=self._download_worker,
                args=(url, dest_path),
                daemon=True
            )
            self._thread.start()
            return {"ok": True, "message": f"Started download for {filename}"}

    def _download_worker(self, url: str, dest_path: Path):
        temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AriChat-Updater/1.0"})
            with urllib.request.urlopen(req, timeout=30.0) as resp, open(temp_path, "wb") as out_file:
                total_size = int(resp.headers.get("Content-Length", 0))
                with self._lock:
                    self._download_state["total_bytes"] = total_size

                downloaded = 0
                chunk_size = 1024 * 512  # 512 KB chunks
                start_time = time.time()
                last_time = start_time
                last_downloaded = 0

                while True:
                    if self._stop_requested:
                        with self._lock:
                            self._download_state.update({
                                "status": "cancelled",
                                "message": "Update download cancelled by user"
                            })
                        if temp_path.exists():
                            temp_path.unlink()
                        return

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break

                    out_file.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    dt = now - last_time
                    if dt >= 0.5:
                        speed = (downloaded - last_downloaded) / dt / (1024 * 1024)
                        percent = min(100.0, (downloaded / total_size * 100.0)) if total_size > 0 else 0.0
                        remaining = total_size - downloaded
                        eta = int(remaining / (speed * 1024 * 1024)) if speed > 0 and remaining > 0 else 0

                        with self._lock:
                            self._download_state.update({
                                "bytes_downloaded": downloaded,
                                "percent": round(percent, 1),
                                "speed_mbps": round(speed, 2),
                                "eta_seconds": eta,
                                "message": f"Downloading... {percent:.1f}% ({speed:.1f} MB/s)"
                            })
                        last_time = now
                        last_downloaded = downloaded

            if temp_path.exists():
                if dest_path.exists():
                    dest_path.unlink()
                temp_path.rename(dest_path)

            with self._lock:
                self._download_state.update({
                    "status": "ready_to_install",
                    "percent": 100.0,
                    "bytes_downloaded": downloaded,
                    "message": "Update downloaded and ready to install!",
                    "installer_path": str(dest_path)
                })
        except Exception as e:
            logger.error(f"Error downloading update: {e}")
            with self._lock:
                self._download_state.update({
                    "status": "error",
                    "message": f"Download failed: {str(e)}"
                })
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def cancel_download(self) -> Dict[str, Any]:
        with self._lock:
            self._stop_requested = True
            return {"ok": True, "message": "Cancelling download..."}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._download_state)

    def apply_update(self) -> Dict[str, Any]:
        """Launches the downloaded installer and terminates current application process cleanly."""
        with self._lock:
            installer_path = self._download_state.get("installer_path")
            if not installer_path or not os.path.isfile(installer_path):
                # Search UPDATES_DIR for any .exe installer
                candidates = list(UPDATES_DIR.glob("*.exe"))
                if candidates:
                    installer_path = str(candidates[0])
                else:
                    return {"ok": False, "message": "No installer file found on disk to apply."}

        logger.info(f"Applying update with installer: {installer_path}")
        try:
            from app.services.engine_service import stop_standalone_engine
            stop_standalone_engine()

            if sys.platform == "win32":
                # Launch installer with lowest privileges flag or standard wizard
                subprocess.Popen([installer_path], shell=False)
            else:
                subprocess.Popen(["xdg-open", installer_path] if sys.platform.startswith("linux") else ["open", installer_path])

            # Schedule clean exit
            def exit_soon():
                time.sleep(1.0)
                os._exit(0)

            threading.Thread(target=exit_soon, daemon=True).start()
            return {"ok": True, "message": "Launching installer and updating Ari Chat..."}
        except Exception as e:
            logger.error(f"Failed to launch update installer: {e}")
            return {"ok": False, "message": f"Could not launch installer: {e}"}

updater_service = UpdaterService()
