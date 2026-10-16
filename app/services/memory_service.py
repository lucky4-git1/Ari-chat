import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Memory

def get_user_memories(db: Session, user_id: int) -> List[Memory]:
    """Retrieves all stored long-term memories for the given user ordered by recency."""
    return db.query(Memory).filter(Memory.user_id == user_id).order_by(Memory.updated_at.desc()).all()

def format_memory_context(memories: List[Memory]) -> str:
    """Formats stored memories into a clean, structured context block for Ari's system prompt."""
    if not memories:
        return ""
    
    # Categorize memories for structured presentation
    grouped: Dict[str, List[str]] = {
        "Instructions & Preferences": [],
        "Identity & Background": [],
        "Technical Stack & Work": [],
        "Projects & Goals": [],
        "Personal & Life": []
    }
    
    cat_map = {
        "instruction": "Instructions & Preferences",
        "preference": "Instructions & Preferences",
        "profile": "Identity & Background",
        "work": "Technical Stack & Work",
        "tech": "Technical Stack & Work",
        "project": "Projects & Goals",
        "fact": "Personal & Life",
        "personal": "Personal & Life"
    }

    for m in memories:
        category_name = cat_map.get(m.category.lower(), "Personal & Life")
        grouped[category_name].append(f"- {m.key}: {m.value}")

    lines = ["### Persistent User Context & Memory (Remembered across all chats):"]
    lines.append("Use the following facts, preferences, and instructions naturally to tailor your responses without explicitly reciting this list unless asked:")
    
    has_content = False
    for group_title, items in grouped.items():
        if items:
            has_content = True
            lines.append(f"\n[{group_title}]")
            lines.extend(items)

    if not has_content:
        return ""

    lines.append("\nStrict Rule: Always adhere to the user's stated preferences, coding standards, and background above.")
    return "\n".join(lines)

def detect_and_store_memory(db: Session, user_id: int, user_message: str) -> List[Dict[str, str]]:
    """
    Intelligent, autonomous memory extraction engine.
    Analyzes user message for personal identity, tech stack, coding preferences,
    dietary restrictions, work roles, projects, and explicit instructions.
    Deduplicates and updates existing memories cleanly.
    """
    msg = user_message.strip()
    if len(msg) < 5:
        return []

    # Comprehensive extraction rules: (regex, key_name, category, value_formatter)
    rules = [
        # Explicit Instructions
        (r"(?:please\s+)?remember (?:that\s+)?(.+)", "Instruction", "instruction", "{0}"),
        (r"(?:from now on|going forward|always)\s+(?:please\s+)?(keep\s+.+|use\s+.+|respond\s+.+|write\s+.+|provide\s+.+|do not\s+.+|don't\s+.+)", "Response Preference", "instruction", "{0}"),
        (r"(?:never|do not|don't)\s+(?:ever\s+)?(use\s+.+|write\s+.+|give\s+.+|explain\s+.+|include\s+.+)", "Constraint", "instruction", "Avoid {0}"),
        (r"(?:i prefer|my preference is for|i like responses that are|keep your answers|answer in a?)\s+([a-zA-Z0-9_\s\-\,\.]{3,60})", "Answer Style", "preference", "Prefers {0}"),
        (r"(?:no comments|without comments|dont add comments|no explanations|code only|only code)", "Coding Preference", "instruction", "Prefers clean code without comments or filler"),

        # Identity & Profile
        (r"(?:my name is|call me|i'm called|myself)\s+([A-Za-z0-9_\-]+(?:\s+(?!and\b|who\b|i\b|im\b|i'm\b|based\b|from\b|living\b)[A-Za-z0-9_\-]+)?)", "Name", "profile", "{0}"),
        (r"^(?:i am|i'm)\s+([A-Za-z0-9_\-]+(?:\s+(?!and\b|who\b|i\b|im\b|i'm\b|a\b|an\b|the\b)[A-Za-z0-9_\-]+)?)(?:$|[,\.\!\?])", "Name", "profile", "{0}"),
        (r"(?:i live in|i am based in|i'm based in|i moved to|my city is|my location is)\s+([A-Za-z0-9_\s\,\.\-]{2,40})", "Location", "profile", "Based in {0}"),
        (r"(?:i speak|my native language is|my primary language is)\s+([A-Za-z]{3,25})", "Language", "profile", "Speaks {0}"),
        (r"(?:i am\s+)?(\d{1,2})\s+years? old", "Age", "profile", "{0} years old"),

        # Work & Profession
        (r"(?:i work as an?|my job is|my profession is|i am an?)\s+([a-zA-Z0-9_\s\-\/]{3,45})(?:\s+at\s+([A-Za-z0-9_\s\.\-]{2,30}))?", "Profession/Role", "work", "{0}{1}"),
        (r"(?:i study|i'm studying|i'm a student at|i go to)\s+([a-zA-Z0-9_\s\.\-]{3,50})", "Education", "profile", "Studying {0}"),

        # Tech Stack, Languages & Tools
        (r"(?:my tech stack is|i code in|i program in|my main language is|i use)\s+([a-zA-Z0-9_\s\+\#\,\.]{2,60})", "Tech Stack", "tech", "Uses {0}"),
        (r"(?:i use|my operating system is|i am on|i'm on)\s+(windows(?:\s+11|\s+10)?(?:\s+with\s+wsl\d?)?|macos(?:\s+[a-zA-Z0-9]+)?|linux(?:\s+ubuntu|\s+arch|\s+debian|\s+fedora)?)", "Operating System", "tech", "{0}"),
        (r"(?:my preferred framework is|i build with|we use)\s+([a-zA-Z0-9_\s\+\#\,\.\-]{2,50})", "Framework/Tools", "tech", "Works with {0}"),
        (r"(?:my database is|we use database|our db is)\s+([a-zA-Z0-9_\s]{2,30})", "Database", "tech", "Uses {0}"),

        # Projects & Goals
        (r"(?:i am building|i'm building|my project is|i am developing|working on a project called)\s+([a-zA-Z0-9_\s\-\.]{3,60})", "Current Project", "project", "Building {0}"),
        (r"(?:my goal is to|i want to learn|aiming to)\s+([a-zA-Z0-9_\s\-\.]{3,60})", "Goal", "project", "Goal: {0}"),

        # Personal Life & Dietary
        (r"(?:i am allergic to|i have an allergy to)\s+([a-zA-Z0-9_\s\,\.]{3,40})", "Allergy / Health", "personal", "Allergic to {0}"),
        (r"(?:i am a|i'm a)\s+(vegan|vegetarian|pescatarian|celiac|diabetic)", "Dietary Preference", "personal", "{0}"),
        (r"(?:i have a dog named|my dog's name is|my cat's name is|i have a pet named)\s+([A-Za-z0-9_\-]+)", "Pet", "personal", "{0}"),
        (r"(?:my hobby is|in my free time i|i love to play|i enjoy playing)\s+([a-zA-Z0-9_\s\,\.]{3,50})", "Hobby & Interest", "personal", "Enjoys {0}")
    ]

    extracted_memories = []

    for item in rules:
        pattern, key_name, category, val_format = item
        match = re.search(pattern, msg, re.IGNORECASE)
        if match:
            groups = match.groups()
            raw_val = groups[0].strip().rstrip(".,!?") if groups and groups[0] else ""
            
            # Additional captured group (e.g. company name)
            extra = ""
            if len(groups) > 1 and groups[1]:
                extra = f" at {groups[1].strip().rstrip('.,!?')}"

            if len(raw_val) >= 2:
                formatted_val = val_format.format(raw_val, extra).strip()

                # Cleanup common trailing words or fluff
                formatted_val = re.sub(r"\s+", " ", formatted_val)

                # Check if this memory already exists or updates an existing memory
                existing = db.query(Memory).filter(
                    Memory.user_id == user_id,
                    Memory.key == key_name
                ).first()

                if existing:
                    # Update value if changed
                    if existing.value.lower() != formatted_val.lower():
                        existing.value = formatted_val
                        existing.category = category
                        existing.updated_at = datetime.utcnow()
                        db.commit()
                        extracted_memories.append({"key": key_name, "value": formatted_val, "action": "updated"})
                else:
                    # Create new memory
                    new_mem = Memory(
                        user_id=user_id,
                        key=key_name,
                        value=formatted_val,
                        category=category
                    )
                    db.add(new_mem)
                    db.commit()
                    extracted_memories.append({"key": key_name, "value": formatted_val, "action": "added"})

    return extracted_memories
