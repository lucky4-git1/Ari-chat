from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.db.database import get_db
from app.db.models import User, Memory
from app.api.auth_routes import get_current_user
from app.services.memory_service import get_user_memories

router = APIRouter(prefix="/api/memories", tags=["memories"])

class MemoryCreateRequest(BaseModel):
    key: str
    value: str
    category: Optional[str] = "preference"

@router.get("/")
def list_memories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memories = get_user_memories(db, user.id)
    return [
        {
            "id": m.id,
            "key": m.key,
            "value": m.value,
            "category": m.category,
            "updated_at": m.updated_at.isoformat()
        }
        for m in memories
    ]

@router.post("/")
def create_memory(req: MemoryCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if key exists
    mem = db.query(Memory).filter(Memory.user_id == user.id, Memory.key == req.key).first()
    if mem:
        mem.value = req.value
        mem.category = req.category or "preference"
    else:
        mem = Memory(
            user_id=user.id,
            key=req.key,
            value=req.value,
            category=req.category or "preference"
        )
        db.add(mem)
    db.commit()
    db.refresh(mem)
    return {
        "id": mem.id,
        "key": mem.key,
        "value": mem.value,
        "category": mem.category
    }

@router.delete("/{memory_id}")
def delete_memory(memory_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem = db.query(Memory).filter(Memory.id == memory_id, Memory.user_id == user.id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(mem)
    db.commit()
    return {"status": "deleted", "id": memory_id}

@router.delete("/")
def clear_all_memories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Memory).filter(Memory.user_id == user.id).delete()
    db.commit()
    return {"status": "all_cleared"}
