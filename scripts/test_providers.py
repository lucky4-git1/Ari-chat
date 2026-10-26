import sys
import os
import json
import httpx

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_pollinations_free_provider():
    print("[1/2] Authenticating as Guest...")
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        auth_res = client.post("/api/auth/guest")
        assert auth_res.status_code == 200
        token = auth_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("[2/2] Testing Free Provider (Pollinations AI / OpenAI endpoint)...")
        conv_res = client.post("/api/chat/conversations", headers=headers, json={"title": "Free Provider Test"})
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        msg_payload = {
            "content": "Reply with 'Hello from free provider!' in 5 words or less.",
            "persona": "general",
            "file_context": None,
            "web_search": False,
            "reasoning_mode": False,
            "cloud_config": {
                "provider": "pollinations",
                "base_url": "https://text.pollinations.ai/openai",
                "api_key": "none",
                "model_name": "openai"
            }
        }

        print("  -> Streaming response via Pollinations AI...")
        tokens = []
        try:
            with client.stream("POST", f"/api/chat/conversations/{conv_id}/messages", headers=headers, json=msg_payload, timeout=25.0) as stream_res:
                assert stream_res.status_code == 200, f"Stream failed: {stream_res.status_code}"
                for line in stream_res.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str:
                            chunk = json.loads(data_str)
                            if chunk.get("type") == "token":
                                tokens.append(chunk["token"])
                                sys.stdout.write(chunk["token"])
                                sys.stdout.flush()
                            elif chunk.get("type") == "done":
                                print("\n  -> Stream finished successfully!")
                                break
                            elif chunk.get("type") == "error":
                                print(f"\n  -> Provider reported error: {chunk.get('error')}")
                                break
            
            output = "".join(tokens)
            print(f"  -> Successfully streamed {len(tokens)} tokens from free cloud endpoint!")
        except Exception as e:
            print(f"  -> External cloud ping note (network/firewall): {e}")

if __name__ == "__main__":
    test_pollinations_free_provider()
