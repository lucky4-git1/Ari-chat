from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.services.model_manager import pull_manager
from app.services.engine_service import get_model_file, start_standalone_engine

router = APIRouter(prefix="/api/models", tags=["models"])

class PullRequest(BaseModel):
    model_id: str = "ari-assistant-3b"

class SwitchRequest(BaseModel):
    model_id: str

@router.get("")
def get_models():
    """Returns list of models with installation status, disk sizes, and descriptions."""
    return {
        "models": pull_manager.list_models(),
        "pull_status": pull_manager.get_status()
    }

@router.post("/pull")
def pull_model(req: PullRequest):
    """Initiates pulling a model from Hugging Face CDN in background."""
    result = pull_manager.start_pull(req.model_id)
    return result

@router.get("/pull-status")
def pull_status():
    """Returns real-time download progress, percentage, transfer speed, and ETA."""
    return pull_manager.get_status()

@router.post("/cancel-pull")
def cancel_pull():
    """Cancels active background model download."""
    return pull_manager.cancel_pull()

@router.post("/switch")
def switch_model(req: SwitchRequest):
    """Switches active embedded engine model if model file exists."""
    target_path = get_model_file(req.model_id)
    if not target_path or not target_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model file for {req.model_id} not found. Please pull it first."
        )
    ok = start_standalone_engine(target_path)
    return {"ok": ok, "model_id": req.model_id, "model_file": target_path.name}
