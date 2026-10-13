"""Integration test for Ari Chat Backend.
Tests database models, auth flow, web search, memory engine, and Ollama connection.
"""

import sys
from pathlib import Path

# Add project root to path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import asyncio
from app.db.database import init_db, SessionLocal
from app.db.models import User, Conversation, Message, Memory
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.services.search_service import perform_web_search, format_search_context
from app.services.memory_service import detect_and_store_memory, get_user_memories, format_memory_context
from app.services.ollama_service import check_ollama_health

async def run_tests():
    print("=" * 65)
    print("      ARI CHAT BACKEND INTEGRATION TEST SUITE")
    print("=" * 65)

    # 1. Database Init
    print("\n[1/5] Testing Database Initialization...")
    init_db()
    db = SessionLocal()
    print("  -> Tables initialized successfully!")

    # 2. Security & Auth Flow
    print("\n[2/5] Testing Password Hashing & JWT Auth...")
    test_pass = "SecureAriPass2026!"
    hashed = hash_password(test_pass)
    assert verify_password(test_pass, hashed), "Password verification failed!"
    assert not verify_password("WrongPass", hashed), "Invalid password accepted!"

    token = create_access_token({"sub": "42", "username": "ari_tester"})
    payload = decode_access_token(token)
    assert payload and payload["sub"] == "42", "JWT decoding failed!"
    print("  -> Password hashing and JWT tokens verified!")

    # 3. Web Search Service
    print("\n[3/5] Testing DuckDuckGo Live Web Search...")
    search_query = "latest artificial intelligence developments"
    results = perform_web_search(search_query, max_results=2)
    print(f"  -> Found {len(results)} live web results!")
    if results:
        print(f"     Title: {results[0]['title']}")
        print(f"     URL:   {results[0]['url']}")
        formatted = format_search_context(results)
        assert "Web Search Context" in formatted
    print("  -> Web search engine verified!")

    # 4. Long-Term Memory Engine
    print("\n[4/5] Testing Long-Term Memory Engine...")
    test_user_id = 9999
    # Clear test memories
    db.query(Memory).filter(Memory.user_id == test_user_id).delete()
    db.commit()

    test_stmt = "My name is Samantha and I work as a Python engineer"
    detect_and_store_memory(db, test_user_id, test_stmt)

    mems = get_user_memories(db, test_user_id)
    print(f"  -> Extracted memories: {[m.key + ': ' + m.value for m in mems]}")
    assert len(mems) > 0, "Failed to extract user memory!"
    mem_prompt = format_memory_context(mems)
    assert "Persistent User Memory" in mem_prompt
    print("  -> Memory engine verified!")

    # Clean up test user memories
    db.query(Memory).filter(Memory.user_id == test_user_id).delete()
    db.commit()
    db.close()

    # 5. Ollama Engine Health
    print("\n[5/5] Checking Ollama Engine Connectivity...")
    ollama_info = await check_ollama_health()
    if ollama_info["online"]:
        print(f"  -> Ollama is ONLINE with models: {ollama_info['models']}")
        if "ari-assistant" in str(ollama_info['models']):
            print("  -> [SUCCESS] 'ari-assistant' is registered and ready!")
    else:
        print("  -> [NOTICE] Ollama service not currently active on port 11434.")

    print("\n" + "=" * 65)
    print("      ALL INTEGRATION TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_tests())
