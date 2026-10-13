import re
from typing import List
from sqlalchemy.orm import Session
from app.db.models import Memory

def get_user_memories(db: Session, user_id: int) -> List[Memory]:
    """Retrieves all stored long-term memories for the given user."""
    return db.query(Memory).filter(Memory.user_id == user_id).order_by(Memory.updated_at.desc()).all()

def format_memory_context(memories: List[Memory]) -> str:
    """Formats stored memories into a prompt block to inject into Ari's system prompt."""
    if not memories:
        return ""
    
    lines = ["### Persistent User Memory (What you know about this user across sessions):"]
    for m in memories:
        lines.append(f"- {m.key}: {m.value}")
    lines.append("Use these details naturally to personalize your answers without explicitly repeating the list unless asked.\n")
    return "\n".join(lines)

def detect_and_store_memory(db: Session, user_id: int, user_message: str):
    """Automatic extractor to capture stated facts and preferences across conversations."""
    msg = user_message.strip()
    
    patterns = [
        (r"(?:my name is|call me|i am called|my name's|myself)\s+([A-Za-z0-9_]+(?:\s+(?!and\b|i\b|who\b|im\b|i'm\b)[A-Za-z0-9_]+)?)", "User Name", "profile"),
        (r"^(?:i am|i'm)\s+([A-Z][a-zA-Z]{1,20})(?:$|[,\.\!\?])", "User Name", "profile"),
        (r"(?:my favorite|i love|i really like)\s+([a-zA-Z0-9_\s]{2,40})", "Favorite", "preference"),
        (r"(?:i prefer|i like to use|my preferred language is|i like coding in)\s+([a-zA-Z0-9_\s\+\#]{2,40})", "Preference", "preference"),
        (r"(?:i work as an?|my profession is|my job is|i am a software engineer|i am a developer)\s+([a-zA-Z0-9_\s]{3,40})", "Profession/Role", "profile"),
        (r"(?:my goal is|i want to learn|i want to build)\s+([a-zA-Z0-9_\s]{3,50})", "Goal", "profile"),
        (r"(?:i am building|i work on|my project is|i'm developing)\s+([a-zA-Z0-9_\s]{3,50})", "Current Project", "project"),
        (r"(?:i live in|i am from|my location is|my city is)\s+([a-zA-Z0-9_\s]{2,40})", "Location", "profile"),
        (r"(?:my hobby is|i enjoy|in my free time i like to)\s+([a-zA-Z0-9_\s]{2,50})", "Interest", "interest"),
        (r"remember (?:that\s+)?(.+)", "Note", "fact")
    ]
    
    for pattern, key_label, category in patterns:
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            extracted_val = match.group(1).strip().rstrip(".,!")
            if len(extracted_val) >= 2:
                # Check if memory key already exists for this user
                existing = db.query(Memory).filter(
                    Memory.user_id == user_id,
                    Memory.key == key_label
                ).first()
                
                if existing:
                    existing.value = extracted_val
                else:
                    new_mem = Memory(
                        user_id=user_id,
                        key=key_label,
                        value=extracted_val,
                        category=category
                    )
                    db.add(new_mem)
                db.commit()
                return {"key": key_label, "value": extracted_val}
    return None
