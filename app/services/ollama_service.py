import json
import logging
import re
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx
from app.core.config import OLLAMA_BASE_URL, DEFAULT_MODEL

logger = logging.getLogger(__name__)

def detect_repetition(text: str, threshold: int = 3) -> Optional[str]:
    """Detects if text contains metadata leaks, hashtag runs, or cyclic repetitions."""
    if not text or len(text) < 4:
        return None

    # Detect metadata headers or special delimiters
    for marker in ["_Static", "Statics", "⏤", "<nooutput>"]:
        if marker in text:
            return marker

    # Detect hashtag runs (#word#word or #yg#yg)
    if "#" in text and len(text.split("#")) >= 3:
        return "#"

    # Detect cyclic substring repetition (e.g. "Intialized.Intialized.Intialized.")
    for l in range(2, 35):
        if len(text) >= l * threshold:
            pattern = text[-l:]
            if text.endswith(pattern * threshold):
                return pattern

    return None

def strip_repeating_suffix(text: str, pattern: str) -> str:
    """Strips all consecutive instances of pattern from the end of text."""
    while text.endswith(pattern):
        text = text[:-len(pattern)]
    return text.rstrip()

def clean_response_text(text: str) -> str:
    """Bulletproof post-processing to clean metadata, non-ASCII garbage, stop tokens, and looping artifacts."""
    if not text:
        return ""
    # Cut off at known stop tokens or metadata markers
    for marker in ["_Static", "Statics", "⏤", "<nooutput>", "<|im_end|>", "<|im_start|>", "<|endoftext|>"]:
        if marker in text:
            text = text.split(marker)[0]
    # Keep printable ASCII, newlines, and tabs
    text = re.sub(r'[^\x20-\x7E\r\n\t]+', '', text)
    # Strip hashtag cascades (#yg#yg or #tag#tag)
    text = re.sub(r'(\#[a-zA-Z0-9_\-]{1,15}){2,}.*$', '', text)
    # Strip any repeating loops
    pat = detect_repetition(text, threshold=3)
    if pat and pat not in ["#", "_Static", "Statics", "⏤", "<nooutput>"]:
        text = strip_repeating_suffix(text, pat)
    return text.strip()

async def check_ollama_health() -> Dict[str, Any]:
    """Checks if Ollama service is reachable and lists available models."""
    url = f"{OLLAMA_BASE_URL}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {"online": True, "models": models}
    except Exception as e:
        logger.warning(f"Ollama connection check failed: {e}")
    return {"online": False, "models": []}

async def stream_chat_completion(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    reasoning_mode: bool = False
) -> AsyncGenerator[str, None]:
    """Streams chat tokens from Ollama with real-time repetition detection and clean termination."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    # Inject reasoning instruction if deep reasoning is turned on
    processed_messages = list(messages)
    if reasoning_mode:
        reasoning_sys = (
            "Thinking Guidelines: Before providing your response, outline your clear logical analysis "
            "and intermediate reasoning steps inside <thought>...</thought> tags. Then provide your direct, "
            "comprehensive response outside the tags."
        )
        if processed_messages and processed_messages[0]["role"] == "system":
            processed_messages[0]["content"] += f"\n\n{reasoning_sys}"
        else:
            processed_messages.insert(0, {"role": "system", "content": reasoning_sys})

    payload = {
        "model": model,
        "messages": processed_messages,
        "stream": True,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.25,
            "repeat_last_n": 64,
            "num_predict": 300,
            "num_ctx": 2048,
            "num_thread": 4,
            "stop": [
                "<|im_end|>",
                "<|im_start|>",
                "<|endoftext|>",
                "<|object_ref_start|>",
                "<|box_start|>",
                "_Static",
                "Statics",
                "⏤",
                "<nooutput>",
                "\n#",
                "\n<|im_start|>",
                "\n<|im_end|>"
            ]
        }
    }

    accumulated = ""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield json.dumps({"error": f"Ollama error: HTTP {response.status_code}"}) + "\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})
                        content = msg.get("content", "")
                        done = chunk.get("done", False)

                        if content:
                            # Filter out non-ASCII garbage or control characters in real time
                            clean_tok = re.sub(r'[^\x20-\x7E\r\n\t]+', '', content)
                            accumulated += clean_tok

                            # Check for stop token leakage
                            for stop_tok in ["<|im_end|>", "<|im_start|>", "<|endoftext|>", "_Static", "Statics", "⏤", "<nooutput>"]:
                                if stop_tok in accumulated:
                                    yield json.dumps({"done": True, "token": ""}) + "\n"
                                    return

                            # Circuit breaker: detect token loops (#yg, Intialized., hashtags)
                            rep_pat = detect_repetition(accumulated, threshold=3)
                            if rep_pat:
                                yield json.dumps({"done": True, "circuit_break": True}) + "\n"
                                return

                            content = clean_tok

                        out_data = {
                            "token": content,
                            "done": done
                        }
                        yield json.dumps(out_data) + "\n"
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Error during Ollama streaming: {e}")
        yield json.dumps({"error": f"Failed to connect to Ari engine: {str(e)}", "done": True}) + "\n"
