import os
import sys
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import BASE_DIR
from app.services.engine_service import MODELS_DIR, find_model_on_disk, start_standalone_engine, stop_standalone_engine

MODEL_CATALOG = {
    "ari-assistant-3b": {
        "id": "ari-assistant-3b",
        "name": "Ari 3B Assistant",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "fallback_filename": "ari_assistant_3b.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_bytes": 2104930304,
        "size_label": "2.0 GB",
        "recommended": True,
        "description": "Official Qwen 2.5 3B Instruct — State-of-the-Art Reasoning & Coding"
    },
    "ari-assistant-1.5b": {
        "id": "ari-assistant-1.5b",
        "name": "Ari 1.5B Assistant",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "fallback_filename": "ari_assistant_1.5b.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_bytes": 1117437952,
        "size_label": "1.0 GB",
        "recommended": False,
        "description": "Official Qwen 2.5 1.5B Instruct — Fast, Lightweight & Accurate"
    }
}

class ModelPullManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._state: Dict[str, Any] = {
            "status": "idle",  # idle, downloading, completed, error, cancelled
            "model_id": None,
            "filename": None,
            "bytes_downloaded": 0,
            "total_bytes": 0,
            "percent": 0.0,
            "speed_mbps": 0.0,
            "eta_seconds": 0,
            "message": "No download in progress"
        }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def list_models(self) -> list:
        models = []
        for m_id, info in MODEL_CATALOG.items():
            model_file = (
                find_model_on_disk(info["filename"]) or
                find_model_on_disk(info.get("fallback_filename", "")) or
                (MODELS_DIR / info["filename"])
            )
            installed = model_file.exists() and model_file.stat().st_size > 10 * 1024 * 1024
            actual_size = model_file.stat().st_size if installed else 0
            models.append({
                "id": info["id"],
                "name": info["name"],
                "filename": info["filename"],
                "size_label": info["size_label"],
                "size_bytes": info["size_bytes"],
                "installed": installed,
                "installed_size": actual_size,
                "recommended": info["recommended"],
                "description": info["description"]
            })
        return models

    def start_pull(self, model_id: str) -> Dict[str, Any]:
        with self._lock:
            if self._state["status"] == "downloading":
                return {
                    "ok": False,
                    "message": f"Download already in progress for {self._state.get('model_id')}"
                }

            if model_id not in MODEL_CATALOG:
                return {"ok": False, "message": f"Unknown model id: {model_id}"}

            info = MODEL_CATALOG[model_id]
            target_file = (
                find_model_on_disk(info["filename"]) or
                find_model_on_disk(info.get("fallback_filename", "")) or
                (MODELS_DIR / info["filename"])
            )
            if target_file.exists() and target_file.stat().st_size > 10 * 1024 * 1024:
                return {
                    "ok": True,
                    "already_installed": True,
                    "message": f"{info['name']} is already installed!"
                }

            self._stop_requested = False
            self._state = {
                "status": "downloading",
                "model_id": model_id,
                "filename": info["filename"],
                "bytes_downloaded": 0,
                "total_bytes": info["size_bytes"],
                "percent": 0.0,
                "speed_mbps": 0.0,
                "eta_seconds": 0,
                "message": f"Starting download of {info['name']}..."
            }

            self._thread = threading.Thread(
                target=self._download_worker,
                args=(info["url"], target_file, model_id, info["name"]),
                daemon=True
            )
            self._thread.start()
            return {"ok": True, "message": f"Download initiated for {info['name']}"}

    def cancel_pull(self) -> Dict[str, Any]:
        with self._lock:
            if self._state["status"] != "downloading":
                return {"ok": False, "message": "No active download to cancel."}
            self._stop_requested = True
            self._state["status"] = "cancelling"
            self._state["message"] = "Cancelling download..."
            return {"ok": True, "message": "Download cancellation requested."}

    def _download_worker(self, url: str, target_file: Path, model_id: str, model_name: str):
        target_file.parent.mkdir(parents=True, exist_ok=True)
        part_file = target_file.with_suffix(target_file.suffix + ".downloading")
        
        start_time = time.time()
        last_update = start_time
        downloaded = 0

        # Support resuming if partial file exists
        mode = "wb"
        headers = {"User-Agent": "AriChat/1.0"}
        if part_file.exists():
            downloaded = part_file.stat().st_size
            mode = "ab"
            headers["Range"] = f"bytes={downloaded}-"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                content_len = resp.headers.get("Content-Length")
                total_len = (int(content_len) + downloaded) if content_len else MODEL_CATALOG[model_id]["size_bytes"]
                
                with open(part_file, mode) as f:
                    chunk_size = 1024 * 512  # 512 KB chunks
                    window_bytes = 0
                    window_time = time.time()
                    
                    while not self._stop_requested:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        window_bytes += len(chunk)
                        
                        now = time.time()
                        if now - last_update >= 0.5:
                            elapsed_window = now - window_time
                            speed_mb = (window_bytes / (1024 * 1024)) / elapsed_window if elapsed_window > 0 else 0.0
                            percent = round((downloaded / total_len) * 100, 1) if total_len else 0.0
                            remaining_bytes = max(0, total_len - downloaded)
                            eta = int(remaining_bytes / (speed_mb * 1024 * 1024)) if speed_mb > 0.05 else 0

                            with self._lock:
                                self._state.update({
                                    "status": "downloading",
                                    "bytes_downloaded": downloaded,
                                    "total_bytes": total_len,
                                    "percent": percent,
                                    "speed_mbps": round(speed_mb, 2),
                                    "eta_seconds": eta,
                                    "message": f"Downloading {model_name}: {downloaded // (1024*1024)} MB / {total_len // (1024*1024)} MB ({percent}%)"
                                })
                            
                            last_update = now
                            window_bytes = 0
                            window_time = now

            if self._stop_requested:
                with self._lock:
                    self._state.update({
                        "status": "cancelled",
                        "message": "Download cancelled by user."
                    })
                return

            # Atomically rename .downloading to target .gguf
            if part_file.exists():
                if target_file.exists():
                    target_file.unlink()
                part_file.rename(target_file)

            with self._lock:
                self._state.update({
                    "status": "completed",
                    "percent": 100.0,
                    "bytes_downloaded": downloaded,
                    "total_bytes": downloaded,
                    "speed_mbps": 0.0,
                    "eta_seconds": 0,
                    "message": f"{model_name} downloaded successfully! Ready to chat."
                })

        except Exception as e:
            with self._lock:
                self._state.update({
                    "status": "error",
                    "message": f"Download failed: {str(e)}"
                })

# Global singleton instance
pull_manager = ModelPullManager()
