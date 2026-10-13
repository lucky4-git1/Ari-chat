import os
import sys
import json
import logging
import re
import subprocess
import asyncio
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Any, Optional
import httpx

from app.core.config import OLLAMA_BASE_URL, DEFAULT_MODEL, BASE_DIR, DATA_DIR

logger = logging.getLogger(__name__)

STANDALONE_BASE_URL = os.getenv("STANDALONE_ENGINE_URL", "http://127.0.0.1:8080")
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
DEFAULT_GGUF_PATH = MODELS_DIR / "ari_assistant_1.5b.gguf"

_ENGINE_PROCESS: Optional[subprocess.Popen] = None

def get_engine_executable() -> Optional[Path]:
    """Returns the path to the standalone llama-server executable if present."""
    exe_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    exe_path = BIN_DIR / exe_name
    return exe_path if exe_path.exists() else None

def get_model_file() -> Optional[Path]:
    """Locates the GGUF model file."""
    if DEFAULT_GGUF_PATH.exists():
        return DEFAULT_GGUF_PATH
    
    # Check fallback in parent artifacts
    alt_path = BASE_DIR.parent / "artifacts" / "checkpoints" / "ari_assistant_1.5b.gguf"
    if alt_path.exists():
        return alt_path
    
    # Check any .gguf in models directory
    if MODELS_DIR.exists():
        for f in MODELS_DIR.glob("*.gguf"):
            return f
            
    return None

def start_standalone_engine() -> bool:
    """Launches llama-server in background if not already running."""
    global _ENGINE_PROCESS
    if _ENGINE_PROCESS is not None and _ENGINE_PROCESS.poll() is None:
        logger.info("Standalone engine is already running.")
        return True

    exe = get_engine_executable()
    model = get_model_file()

    if not exe or not model:
        logger.warning(f"Cannot auto-start standalone engine. Exe: {exe}, Model: {model}")
        return False

    log_path = DATA_DIR / "llama_server.log"
    logger.info(f"Starting standalone engine: {exe} with model {model} (logging to {log_path})")

    try:
        log_file = open(log_path, "a", encoding="utf-8")
        cmd = [
            str(exe),
            "-m", str(model),
            "-c", "2048",
            "-t", "4",
            "--port", "8080",
            "--host", "127.0.0.1",
            "--temp", "0.7",
            "-cb"  # continuous batching
        ]
        
        # Detached/background flags on Windows
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0

        _ENGINE_PROCESS = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            creationflags=creationflags
        )
        return True
    except Exception as e:
        logger.error(f"Failed to launch standalone engine: {e}")
        return False

def stop_standalone_engine():
    """Stops the standalone llama-server process if launched by this app."""
    global _ENGINE_PROCESS
    if _ENGINE_PROCESS is not None:
        logger.info("Shutting down standalone engine...")
        try:
            _ENGINE_PROCESS.terminate()
            _ENGINE_PROCESS.wait(timeout=5)
        except Exception as e:
            logger.warning(f"Error terminating engine process: {e}")
            try:
                _ENGINE_PROCESS.kill()
            except Exception:
                pass
        _ENGINE_PROCESS = None

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
    # Strip opening synthetic wrappers if present
    text = re.sub(r'^(<response>|<answer>)\s*', '', text, flags=re.IGNORECASE)

    # Cut off at known stop tokens, turn markers, or metadata delimiters
    stop_markers = [
        "</response>",
        "</answer>",
        "<endofconversation>",
        "<startchat>",
        "<|im_end|>",
        "<|im_start|>",
        "<|endoftext|>",
        "_Static",
        "Statics",
        "⏤",
        "<nooutput>",
        "//[",
        "[iVar",
        "Intialized:",
        "Intialized.",
        "Answered.",
        "<br/>",
        "<br>",
        "[view answer]",
        "[\\view answer\\]",
        "<colgroup",
        "<table",
        "<a href",
        "<p class=",
        "<span id=",
        "synthetic ingredients",
        ">delete",
        "ondelete",
        "user deleted",
        "deleted comment",
    ]
    for marker in stop_markers:
        if marker.lower() in text.lower():
            idx = text.lower().find(marker.lower())
            text = text[:idx]

    # Remove any dangling or leftover HTML tags & broken forum links
    text = re.sub(r'\[\\?\[?View Answer\\?\]?\]\([^)]+\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[View Answer\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<a\s+href=[^>]+>.*?</a>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?:table|colgroup|tr|td|th|span|p|div|b|h\d)[^>]*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:table|colgroup|tr|td|th|span|p|div|b|h\d)>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(<br\s*/?|<\s*|/\s*>|/><end.*)$', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:>Delete|onDelete|User deleted).*$', '', text, flags=re.IGNORECASE)
    
    # Strip hashtag cascades or trailing hashtags (#sriyu, #yg#yg)
    text = re.sub(r'(\#[a-zA-Z0-9_\-]{1,15}){2,}.*$', '', text)
    text = re.sub(r'\s*\#[a-zA-Z0-9_\-]{2,20}\s*$', '', text)
    # Keep printable ASCII, newlines, and tabs
    text = re.sub(r'[^\x20-\x7E\r\n\t]+', '', text)
    # Strip any repeating loops
    pat = detect_repetition(text, threshold=3)
    if pat and pat not in ["#", "_Static", "Statics", "⏤", "<nooutput>"]:
        text = strip_repeating_suffix(text, pat)
    
    # Strip web scrape button artifacts like 'Copy', 'Copied'
    text = re.sub(r'^(?:Copy|Copied)\s*\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n(?:Copy|Copied)\s*\n?', '\n', text, flags=re.IGNORECASE)

    # Cut off simulated subsequent user turns
    simulated_turns = [
        r'\n(?:User|Human|Question|Prompt):\s*',
        r'\n###\s*(?:User|Human|Prompt)',
        r'\n(?:make a navbar|how to make|can you make|can u make|what is)\b'
    ]
    for sim in simulated_turns:
        m = re.search(sim, text, re.IGNORECASE)
        if m and m.start() > 20: # ensure we don't cut off immediate start
            text = text[:m.start()]

    # Auto-fence bare HTML code so browsers highlight it instead of executing live elements
    if "```" not in text:
        html_match = re.search(r'<(?:nav|ul|ol|form|html|body|header|footer|section|main|div)\b', text, re.IGNORECASE)
        if html_match:
            start_idx = html_match.start()
            prefix = text[:start_idx].rstrip()
            code_part = text[start_idx:].strip()
            text = f"{prefix}\n\n```html\n{code_part}\n```" if prefix else f"```html\n{code_part}\n```"

    # Auto-close unclosed code fences if generation was truncated mid-code
    if text.count("```") % 2 != 0:
        text = text.rstrip() + "\n```"

    return text.strip()

async def check_engine_health() -> Dict[str, Any]:
    """Checks engine status: Standalone llama-server (primary) or Ollama (fallback)."""
    # 1. Check Standalone llama-server
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{STANDALONE_BASE_URL}/health")
            if res.status_code == 200:
                return {
                    "online": True,
                    "engine": "standalone",
                    "models": ["ari-assistant:1.5b"]
                }
    except Exception:
        pass

    # 2. Check Ollama service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "online": True,
                    "engine": "ollama",
                    "models": models if models else ["ari-assistant:1.5b"]
                }
    except Exception:
        pass

    # 3. Not running, but check if standalone files are present
    has_exe = get_engine_executable() is not None
    has_model = get_model_file() is not None
    return {
        "online": False,
        "engine": "standalone" if (has_exe and has_model) else "none",
        "models": ["ari-assistant:1.5b"] if (has_exe and has_model) else []
    }

# Backward compatibility alias
check_ollama_health = check_engine_health

STOP_WORDS = [
    "<|im_end|>",
    "<|im_start|>",
    "<|endoftext|>",
    "<|object_ref_start|>",
    "<|box_start|>",
    "</response>",
    "</answer>",
    "<endofconversation>",
    "<startchat>",
    "//[",
    "[iVar",
    "<br/>",
    "<br>",
    "Intialized:",
    "Intialized.",
    "Answered.",
    "[View Answer]",
    "[view answer]",
    "<colgroup",
    "<table",
    "<a href",
    "<p class=",
    "Synthetic Ingredients",
    "_Static",
    "Statics",
    "⏤",
    "<nooutput>",
    "\n#",
    "\n<|im_start|>",
    "\n<|im_end|>",
    "\nUser:",
    "\nHuman:",
    "\nQuestion:",
    "\n### User",
    "\n### Human"
]

async def stream_chat_completion(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.35,
    reasoning_mode: bool = False
) -> AsyncGenerator[str, None]:
    """Streams chat tokens from Standalone llama-server (OpenAI format) or Ollama with circuit breakers."""
    health = await check_engine_health()

    # If neither is running, try auto-starting standalone engine
    if not health.get("online"):
        logger.info("Engine offline. Attempting to auto-start standalone engine...")
        if start_standalone_engine():
            # Wait up to 6 seconds for engine to be ready
            for _ in range(12):
                await asyncio.sleep(0.5)
                h = await check_engine_health()
                if h.get("online"):
                    health = h
                    break

    engine_type = health.get("engine", "standalone")

    # Inject reasoning instruction if requested
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

    if engine_type == "standalone" or health.get("online"):
        # Stream from Standalone llama-server (OpenAI-compatible /v1/chat/completions)
        async for item in _stream_standalone(processed_messages, temperature):
            yield item
    else:
        # Stream from Ollama
        async for item in _stream_ollama(processed_messages, model, temperature):
            yield item

async def _stream_standalone(
    messages: List[Dict[str, str]],
    temperature: float = 0.35
) -> AsyncGenerator[str, None]:
    """Streams tokens via OpenAI SSE format from standalone llama-server."""
    url = f"{STANDALONE_BASE_URL}/v1/chat/completions"
    payload = {
        "messages": messages,
        "temperature": temperature,
        "presence_penalty": 0.2,
        "frequency_penalty": 0.3,
        "max_tokens": 1024,
        "stop": STOP_WORDS,
        "stream": True
    }

    accumulated = ""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield json.dumps({"error": f"Engine error: HTTP {response.status_code}"}) + "\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield json.dumps({"token": "", "done": True}) + "\n"
                            break

                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            finish_reason = choices[0].get("finish_reason")

                            done = finish_reason is not None

                            if content:
                                # Clean control characters and check stop sequences
                                clean_tok = re.sub(r'[^\x20-\x7E\r\n\t]+', '', content)
                                accumulated += clean_tok

                                for stop_tok in STOP_WORDS:
                                    if stop_tok.lower() in accumulated.lower():
                                        yield json.dumps({"done": True, "token": "", "circuit_break": True}) + "\n"
                                        return

                                rep_pat = detect_repetition(accumulated, threshold=3)
                                if rep_pat:
                                    yield json.dumps({"done": True, "circuit_break": True}) + "\n"
                                    return

                                yield json.dumps({"token": clean_tok, "done": done}) + "\n"

                            if done:
                                break
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error(f"Error during standalone engine streaming: {e}")
        yield json.dumps({"error": f"Engine error: {str(e)}", "done": True}) + "\n"

async def _stream_ollama(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7
) -> AsyncGenerator[str, None]:
    """Streams chat tokens from Ollama with real-time repetition detection and clean termination."""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.25,
            "repeat_last_n": 64,
            "num_predict": 400,
            "num_ctx": 2048,
            "num_thread": 4,
            "stop": STOP_WORDS
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
                            clean_tok = re.sub(r'[^\x20-\x7E\r\n\t]+', '', content)
                            accumulated += clean_tok

                            for stop_tok in STOP_WORDS:
                                if stop_tok.lower() in accumulated.lower():
                                    yield json.dumps({"done": True, "token": "", "circuit_break": True}) + "\n"
                                    return

                            rep_pat = detect_repetition(accumulated, threshold=3)
                            if rep_pat:
                                yield json.dumps({"done": True, "circuit_break": True}) + "\n"
                                return

                            content = clean_tok

                        yield json.dumps({"token": content, "done": done}) + "\n"
                        if done:
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Error during Ollama streaming: {e}")
        yield json.dumps({"error": f"Failed to connect to Ari engine: {str(e)}", "done": True}) + "\n"
