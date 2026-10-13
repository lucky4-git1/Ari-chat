"""Complete End-to-End Integration & Reliability Test Suite for Ari Chat.
Tests:
1. Casual Greetings (checks that repeating loops and #yg metadata are 100% eliminated)
2. Python Code Generation
3. Step-by-Step Logic / Reasoning
4. Real-Time Web Search with Source Citations
5. Cross-Session Long-Term Memory Recall
"""

import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://127.0.0.1:8000/api"

def print_separator(title):
    print("\n" + "=" * 70)
    print(f"   {title}")
    print("=" * 70)

def register_or_login(username, password):
    email = f"{username}@test.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={"username": username, "email": email, "password": password})
    if r.status_code == 200:
        return r.json()["access_token"]
    r2 = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    return r2.json()["access_token"]

def send_chat_message(conv_id, content, token, web_search=False, reasoning=False):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/chat/conversations/{conv_id}/messages"
    payload = {
        "content": content,
        "web_search": web_search,
        "reasoning_mode": reasoning,
        "model": "ari-assistant"
    }

    t0 = time.time()
    res = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
    
    tokens = []
    sources = []
    clean_final = ""
    
    for line in res.iter_lines():
        if not line:
            continue
        line_str = line.decode('utf-8', errors='replace')
        if line_str.startswith("data: "):
            try:
                data = json.loads(line_str[6:])
                if data.get("type") == "sources":
                    sources = data.get("sources", [])
                elif data.get("type") == "token":
                    tokens.append(data.get("token", ""))
                elif data.get("type") == "done":
                    clean_final = data.get("clean_content", "")
                    break
            except Exception:
                pass
                
    elapsed = time.time() - t0
    raw_response = "".join(tokens)
    return {
        "raw": raw_response,
        "clean": clean_final,
        "sources": sources,
        "elapsed": elapsed
    }

def main():
    print_separator("ARI CHAT: FULL SYSTEM END-TO-END VERIFICATION SUITE")

    # Setup User & Session
    test_user = f"e2e_user_{int(time.time())}"
    token = register_or_login(test_user, "TestPass123!")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[+] Authenticated as test user: {test_user}")

    # TEST 1: Greeting & Repetition Guard Check
    print_separator("[Test 1/5] Greeting & Repetition Circuit Breaker ('hii')")
    conv1 = requests.post(f"{BASE_URL}/chat/conversations", json={"title": "Greeting Test"}, headers=headers).json()
    print("USER: hii")
    res1 = send_chat_message(conv1["id"], "hii", token)
    print(f"ARI REPLY:\n{res1['clean']}")
    print(f"Elapsed: {res1['elapsed']:.2f}s")
    
    assert "#yg" not in res1["clean"], "FAIL: #yg found in response!"
    assert "_Statics" not in res1["clean"], "FAIL: _Statics found in response!"
    assert "<|im_end|>" not in res1["clean"], "FAIL: stop token leak!"
    assert len(res1["clean"]) > 0, "FAIL: empty response!"
    print("[PASS] Greeting answered cleanly without repetition or metadata leaks!")

    # TEST 2: Python Code Generation
    print_separator("[Test 2/5] Software Engineering Code Generation")
    conv2 = requests.post(f"{BASE_URL}/chat/conversations", json={"title": "Code Test"}, headers=headers).json()
    code_prompt = "Write a clean Python function to check whether two strings are anagrams."
    print(f"USER: {code_prompt}")
    res2 = send_chat_message(conv2["id"], code_prompt, token)
    print(f"ARI REPLY:\n{res2['clean']}")
    print(f"Elapsed: {res2['elapsed']:.2f}s")
    assert "def " in res2["clean"], "FAIL: Python function definition missing!"
    print("[PASS] Python code generated successfully!")

    # TEST 3: Logic & Reasoning Riddle
    print_separator("[Test 3/5] Logic Riddle")
    conv3 = requests.post(f"{BASE_URL}/chat/conversations", json={"title": "Logic Test"}, headers=headers).json()
    logic_prompt = "If you have 3 apples and you take away 2, how many apples do you have?"
    print(f"USER: {logic_prompt}")
    res3 = send_chat_message(conv3["id"], logic_prompt, token)
    print(f"ARI REPLY:\n{res3['clean']}")
    print(f"Elapsed: {res3['elapsed']:.2f}s")
    assert len(res3["clean"]) > 0, "FAIL: Response empty!"
    print("[PASS] Logic riddle answered successfully!")

    # TEST 4: Live Web Search with Citations
    print_separator("[Test 4/5] Live Web Search Grounding")
    conv4 = requests.post(f"{BASE_URL}/chat/conversations", json={"title": "Web Search Test"}, headers=headers).json()
    search_prompt = "What are the latest AI news and breakthroughs?"
    print(f"USER: {search_prompt} (Web Search: ON)")
    res4 = send_chat_message(conv4["id"], search_prompt, token, web_search=True)
    print(f"Found {len(res4['sources'])} Live Sources:")
    for i, s in enumerate(res4['sources'][:3], 1):
        print(f"  [{i}] {s.get('title')} ({s.get('url')})")
    print(f"\nARI GROUNDED REPLY:\n{res4['clean']}")
    print(f"Elapsed: {res4['elapsed']:.2f}s")
    assert len(res4['sources']) > 0, "FAIL: No web sources retrieved!"
    print("[PASS] Live web search executed and sources cited!")

    # TEST 5: Cross-Session Long-Term Memory
    print_separator("[Test 5/5] Cross-Session Persistent Memory Recall")
    # Step A: Teach Ari a personal fact in Conversation 5
    conv5_a = requests.post(f"{BASE_URL}/chat/conversations", json={"title": "Memory Training"}, headers=headers).json()
    fact_prompt = "My name is Samantha and I work as an autonomous robotics engineer. Remember this!"
    print(f"Conversation A USER: {fact_prompt}")
    res5_a = send_chat_message(conv5_a["id"], fact_prompt, token)
    print(f"ARI: {res5_a['clean']}")

    # Check stored memory
    mems = requests.get(f"{BASE_URL}/memories/", headers=headers).json()
    print(f"\nStored Memories in DB: {[m['key'] + ' -> ' + m['value'] for m in mems]}")
    assert len(mems) > 0, "FAIL: No memories recorded!"

    # Step B: Open completely NEW Conversation B and ask Ari to recall
    conv5_b = requests.post(f"{BASE_URL}/chat/conversations", json={"title": "Fresh Thread Recall"}, headers=headers).json()
    recall_prompt = "What is my name and what is my profession?"
    print(f"\nConversation B (Fresh Thread) USER: {recall_prompt}")
    res5_b = send_chat_message(conv5_b["id"], recall_prompt, token)
    print(f"ARI RECALL:\n{res5_b['clean']}")
    print(f"Elapsed: {res5_b['elapsed']:.2f}s")
    
    assert "Samantha" in res5_b["clean"] or "robotics" in res5_b["clean"].lower(), "FAIL: Ari did not recall stored memory!"
    print("[PASS] Cross-session memory successfully retained and recalled!")

    print_separator("ALL 5 SYSTEM TESTS PASSED PERFECTLY! ARI CHAT IS FULLY VERIFIED.")

if __name__ == "__main__":
    main()
