from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.core.config import VERSION
from app.services.updater_service import updater_service

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/version")
def get_version():
    """Returns current Ari Chat app version."""
    return {"version": VERSION}

@router.get("/update/check")
def check_update():
    """Checks GitHub for new application versions."""
    return updater_service.check_for_update()

@router.post("/update/download")
def download_update():
    """Starts background download of new version."""
    return updater_service.start_download()

@router.get("/update/status")
def update_status():
    """Returns download percentage, speed, and status."""
    return updater_service.get_status()

@router.post("/update/cancel")
def cancel_update():
    """Cancels active update download."""
    return updater_service.cancel_download()

@router.post("/update/apply")
def apply_update():
    """Launches downloaded installer and exits app."""
    return updater_service.apply_update()
