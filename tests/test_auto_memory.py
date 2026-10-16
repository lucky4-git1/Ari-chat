import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.database import SessionLocal, init_db
from app.services.memory_service import detect_and_store_memory, get_user_memories, format_memory_context
from app.db.models import User

init_db()
db = SessionLocal()
user = db.query(User).first()
if not user:
    user = User(username='test_user', password_hash='hash')
    db.add(user)
    db.commit()

test_phrases = [
    'My name is David and I live in Seattle.',
    'I work as a Senior Backend Engineer at Stripe.',
    'My tech stack is Python, FastAPI and PostgreSQL.',
    'Always provide TypeScript code without comments.',
    'Remember that I am allergic to peanuts.',
    'I have a dog named Bruno.',
    'I moved to San Francisco.'
]

print("--- TESTING AUTOMATIC MEMORY EXTRACTION ---")
for phrase in test_phrases:
    extracted = detect_and_store_memory(db, user.id, phrase)
    print(f'User message: "{phrase}"')
    print(f" -> Extracted/Updated: {extracted}\n")

memories = get_user_memories(db, user.id)
print(f"Total stored memories: {len(memories)}")
prompt_block = format_memory_context(memories)
print("\n--- FORMATTED CONTEXT INJECTED INTO MODEL PROMPT ---")
print(prompt_block)
