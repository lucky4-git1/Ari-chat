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

_CURRENT_MODEL_PATH: Optional[Path] = None

def get_engine_executable() -> Optional[Path]:
    """Returns the path to the standalone llama-server executable if present."""
    exe_name = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    search_dirs = [
        BIN_DIR,
        Path(sys.executable).resolve().parent / "bin" if getattr(sys, "frozen", False) else BIN_DIR,
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "AriChat" / "bin",
        Path("C:/Program Files/AriChat/bin"),
        Path("C:/Program Files (x86)/AriChat/bin"),
    ]
    for d in search_dirs:
        cand = d / exe_name
        if cand.exists():
            return cand
    return None

def find_model_on_disk(filename: str) -> Optional[Path]:
    """Scans all possible model directory locations for the GGUF file."""
    search_dirs = [
        MODELS_DIR,
        Path(sys.executable).resolve().parent / "models" if getattr(sys, "frozen", False) else MODELS_DIR,
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "AriChat" / "models",
        Path(os.environ.get("LOCALAPPDATA", "")) / "AriChat" / "models",
        Path("C:/Program Files/AriChat/models"),
        Path("C:/Program Files (x86)/AriChat/models"),
        BASE_DIR.parent / "artifacts" / "checkpoints",
        BASE_DIR.parent,
    ]
    for d in search_dirs:
        try:
            cand = d / filename
            if cand.exists() and cand.stat().st_size > 100 * 1024 * 1024:
                return cand
        except Exception:
            pass
    return None

def list_available_models() -> List[str]:
    """Scans models directory strictly for installed assistant GGUF models (3B and 1.5B)."""
    models = []
    has_3b = find_model_on_disk("qwen2.5-3b-instruct-q4_k_m.gguf") or find_model_on_disk("ari_assistant_3b.gguf")
    has_15b = find_model_on_disk("qwen2.5-1.5b-instruct-q4_k_m.gguf") or find_model_on_disk("ari_assistant_1.5b.gguf")
    if has_3b:
        models.append("ari-assistant-3b")
    if has_15b:
        models.append("ari-assistant-1.5b")
    if not models:
        models = ["ari-assistant-3b", "ari-assistant-1.5b"]
    return models

def get_model_file(requested_model: Optional[str] = None) -> Optional[Path]:
    """Locates the GGUF model file for the requested model (1.5B or 3B), falling back gracefully."""
    m3b = find_model_on_disk("qwen2.5-3b-instruct-q4_k_m.gguf") or find_model_on_disk("ari_assistant_3b.gguf")
    m15b = find_model_on_disk("qwen2.5-1.5b-instruct-q4_k_m.gguf") or find_model_on_disk("ari_assistant_1.5b.gguf")

    if requested_model:
        req = requested_model.lower().replace("-", "_")
        if "3b" in req:
            return m3b or m15b
        elif "1.5b" in req:
            return m15b or m3b

    return m3b or m15b

def start_standalone_engine(model_path: Optional[Path] = None) -> bool:
    """Launches llama-server in background with the designated assistant model."""
    global _ENGINE_PROCESS, _CURRENT_MODEL_PATH
    
    exe = get_engine_executable()
    model = model_path or get_model_file()

    if not exe or not model:
        logger.warning(f"Cannot auto-start standalone engine. Exe: {exe}, Model: {model}")
        return False

    if _ENGINE_PROCESS is not None and _ENGINE_PROCESS.poll() is None:
        if _CURRENT_MODEL_PATH and _CURRENT_MODEL_PATH.resolve() == model.resolve():
            logger.info(f"Standalone engine already running with {model.name}")
            return True
        logger.info(f"Switching engine model to {model}...")
        stop_standalone_engine()

    log_path = DATA_DIR / "llama_server.log"
    logger.info(f"Starting standalone engine: {exe} with model {model} (logging to {log_path})")

    try:
        log_file = open(log_path, "a", encoding="utf-8")
        cpu_threads = str(min(os.cpu_count() or 6, 8))
        cmd = [
            str(exe),
            "-m", str(model),
            "-c", "4096",
            "-b", "512",
            "-ub", "512",
            "-t", cpu_threads,
            "-tb", cpu_threads,
            "-np", "1",
            "--repeat-penalty", "1.05",
            "--repeat-last-n", "64",
            "--port", "8080",
            "--host", "127.0.0.1",
            "--temp", "0.7",
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
        _CURRENT_MODEL_PATH = model
        return True
    except Exception as e:
        logger.error(f"Failed to launch standalone engine: {e}")
        return False

def stop_standalone_engine():
    """Stops the standalone llama-server process and releases all port bindings."""
    global _ENGINE_PROCESS, _CURRENT_MODEL_PATH
    if _ENGINE_PROCESS is not None:
        logger.info("Shutting down standalone engine...")
        try:
            _ENGINE_PROCESS.terminate()
            _ENGINE_PROCESS.wait(timeout=2)
        except Exception:
            try:
                _ENGINE_PROCESS.kill()
            except Exception:
                pass
        _ENGINE_PROCESS = None

    # Guaranteed force kill of any lingering llama-server instances to free port 8080
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe"], capture_output=True)
        except Exception:
            pass
    else:
        try:
            subprocess.run(["pkill", "-9", "-f", "llama-server"], capture_output=True)
        except Exception:
            pass
    _CURRENT_MODEL_PATH = None

async def ensure_standalone_engine(model_name: Optional[str] = None) -> bool:
    """Ensures standalone llama-server is running and ready with the designated assistant model."""
    target_path = get_model_file(model_name)
    if not target_path or not target_path.exists():
        target_path = get_model_file()
        if not target_path or not target_path.exists():
            return False

    # 1. Check if engine is running and responding
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{STANDALONE_BASE_URL}/health")
            if res.status_code == 200:
                # Engine is healthy and ready. Check if loaded model matches target
                props_res = await client.get(f"{STANDALONE_BASE_URL}/props")
                if props_res.status_code == 200:
                    current_alias = props_res.json().get("model_alias", "")
                    if current_alias and Path(current_alias).resolve() == target_path.resolve():
                        return True
                    # Different model requested: switch model
                    logger.info(f"Model switch detected: running={current_alias}, requested={target_path}")
                    stop_standalone_engine()
                    await asyncio.sleep(0.5)
            elif res.status_code == 503:
                # Engine is currently initializing / loading weights - wait for it!
                logger.info("Engine is loading model. Waiting for readiness...")
                for _ in range(30):
                    await asyncio.sleep(0.5)
                    try:
                        h = await client.get(f"{STANDALONE_BASE_URL}/health")
                        if h.status_code == 200:
                            return True
                    except Exception:
                        pass
    except Exception:
        pass

    # 2. Launch engine with target model if not already up
    if not start_standalone_engine(target_path):
        return False

    # 3. Wait up to 20 seconds for engine /health to become 200
    for _ in range(40):
        await asyncio.sleep(0.5)
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(f"{STANDALONE_BASE_URL}/health")
                if res.status_code == 200:
                    return True
        except Exception:
            pass

    return False

def detect_repetition(text: str, threshold: int = 3) -> Optional[str]:
    """Universal repetition detection: detects metadata leaks, hashtag runs, duplicate sentences/paragraphs, and phrase loops."""
    if not text or len(text) < 4:
        return None

    # Detect metadata headers, internal notes, or special delimiters
    for marker in [
        "_Static", "Statics", "⏤", "<nooutput>", ":async:", "async:", "[async]",
        "note to self:", "note to self", "?(", "!(", ".("
    ]:
        if marker in text.lower():
            return marker

    # If we are currently inside a code block (``` or open <style>/<script>), 
    # skip natural language paragraph/sentence deduplication to allow CSS/HTML/code structures
    in_code = (text.count("```") % 2 == 1)
    lower = text.lower()
    if not in_code:
        for tag in ["<style", "<script", "<svg"]:
            close_tag = "</" + tag[1:] + ">"
            if tag in lower and close_tag not in lower[lower.rfind(tag):]:
                in_code = True
                break

    if in_code:
        # Only detect extreme runaway repetition (same code chunk repeated 5+ times)
        for l in range(10, 80):
            if len(text) >= l * 5:
                pattern = text[-l:]
                if not pattern.strip() or not any(c.isalnum() for c in pattern):
                    continue
                if text.endswith(pattern * 5):
                    return pattern
        return None

    # Detect parenthetical prompt/suggestion cascades: e.g. \n(What can I do for you?)\n(How can I assist you?)
    if re.search(r'(\n\s*\([A-Z][^)]*[?!.]?\s*\)){1,}', text) and len(text) > 40:
        return "\n("

    # 1. Universal Paragraph-level duplicate check (detects duplicate paragraphs >= 30 chars)
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) >= 30]
    seen_paras = set()
    for p in paras:
        norm = re.sub(r'[^\w\s]', '', p).lower()
        if not norm or len(norm.strip()) < 10:
            continue
        if norm in seen_paras:
            return p
        seen_paras.add(norm)

    # 2. Universal Sentence-level duplicate check (detects duplicate sentences >= 25 chars)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) >= 25]
    seen_sents = set()
    for s in sentences:
        norm = re.sub(r'[^\w\s]', '', s).lower()
        if not norm or len(norm.strip()) < 10:
            continue
        if norm in seen_sents:
            return s
        seen_sents.add(norm)

    # 3. Universal 8-word sequence duplicate check (detects phrase echoing across sentences)
    words = [w for w in text.lower().split() if any(c.isalnum() for c in w)]
    if len(words) >= 16:
        n = 8
        seen_ngrams = set()
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n])
            if ngram in seen_ngrams:
                return ngram
            seen_ngrams.add(ngram)

    # 4. Detect multi-word / sentence / paragraph cyclic repetitions (threshold=2 for lengths 15 to 1000)
    clean_strip = text.rstrip()
    for l in range(15, min(len(clean_strip) // 2 + 1, 1000)):
        pattern = clean_strip[-l:]
        if not pattern.strip() or len(pattern.strip()) < 8:
            continue
        # Ignore markdown table rows, dividers, horizontal rules, and punctuation borders
        if not any(c.isalnum() for c in pattern):
            continue
        prefix = clean_strip[:-l].rstrip()
        if prefix.endswith(pattern):
            return pattern

    # 5. Detect actual concatenated hashtag cascades (#word#word#word)
    if re.search(r'(?:\#[a-zA-Z0-9_\-]{1,15}){3,}', text):
        return "#"

    # 6. Detect short cyclic substring repetition (e.g. "Intialized.Intialized.Intialized.")
    for l in range(2, 35):
        if len(text) >= l * threshold:
            pattern = text[-l:]
            # Must not be pure whitespace/indentation, and must contain alphanumeric characters
            if not pattern.strip() or not any(c.isalnum() for c in pattern):
                continue
            if text.endswith(pattern * threshold):
                return pattern

    return None

def detect_simulated_turn(text: str) -> bool:
    """Detects if text contains simulated human messages, user prompt tags, or multi-turn conversational leakage."""
    if len(text) < 40:
        return False

    in_code = (text.count("```") % 2 == 1)
    if in_code:
        return False

    patterns = [
        r'</tool_call>',
        r'<tool_call>',
        r'</tool_response>',
        r'<tool_response>',
        r'\n(?:User|Human|Question):\s*',
        r'\n###\s*(?:User|Human|Prompt)',
        r'<\|im_start\|>',
        r'<\|im_end\|>',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m and m.start() > 20:
            return True
    return False

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

    # Strip opening conversational clichés (e.g. "Certainly! Below is...", "Sure! Here are...")
    cliche_pattern = r'^(?:(?:Certainly|Sure|Of course|Definitely|Gladly)(?:!|,|\.)?\s*)?(?:(?:Here(?:|\'s)|\bBelow)\s+(?:is|are)\s+[^:\n]+:?\s*)?\n+'
    text = re.sub(cliche_pattern, '', text, flags=re.IGNORECASE)

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
        ":async:",
        ":async",
        "async:",
        "[async]",
        "//[",
        "[iVar",
        "Intialized:",
        "Intialized.",
        "Answered.",
        "[view answer]",
        "[\\view answer\\]",
        ">delete",
        "ondelete",
        "user deleted",
        "deleted comment",
    ]
    for marker in stop_markers:
        if marker.lower() in text.lower():
            idx = text.lower().find(marker.lower())
            text = text[:idx]

    # Remove forum scrapers like [View Answer]
    text = re.sub(r'\[\\?\[?View Answer\\?\]?\]\([^)]+\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[View Answer\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:>Delete|onDelete|User deleted).*$', '', text, flags=re.IGNORECASE)
    
    # Strip hashtag cascades or trailing hashtags (#sriyu, #yg#yg)
    text = re.sub(r'(\#[a-zA-Z0-9_\-]{1,15}){2,}.*$', '', text)
    text = re.sub(r'\s*\#[a-zA-Z0-9_\-]{2,20}\s*$', '', text)
    # Keep printable ASCII, newlines, and tabs
    # Universal paragraph deduplication: truncate before the first duplicate paragraph (preserves newlines, lists, and formatting)
    paras = text.split('\n')
    seen_paras = set()
    kept_paras = []
    for p in paras:
        p_clean = p.strip()
        if len(p_clean) >= 30:
            norm = re.sub(r'[^\w\s]', '', p_clean).lower()
            if norm in seen_paras:
                break
            seen_paras.add(norm)
        kept_paras.append(p)
    text = '\n'.join(kept_paras)

    # Strip repeating loops
    pat = detect_repetition(text, threshold=3)
    if pat and pat not in ["#", "_Static", "Statics", "⏤", "<nooutput>"]:
        text = strip_repeating_suffix(text, pat)

    # Strip parenthetical alternative prompt / suggestion lists (e.g. (Have a nice day!), \n(What can I do for you?))
    text = re.sub(r'(\?|\.|\!)\s*\([A-Z][^)]*[?!.]?\).*$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'(\n\s*\([A-Z][^)]*[?!.]?\s*\)){1,}.*$', '', text, flags=re.DOTALL)
    text = re.sub(r'\n*\s*Note(?:\s+to\s+self)?\s*:.*$', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\n\s*\((?:Note|What|How|Is there|Have a|Do you|Feel free|Can I|Need help|Let me know)[^)]*\).*$', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'\n\s*\([A-Z][^)]*[?!]\)\s*$', '', text)
    
    # Strip web scrape button artifacts like 'Copy', 'Copied'
    text = re.sub(r'^(?:Copy|Copied)\s*\n?', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\n(?:Copy|Copied)\s*\n?', '\n', text, flags=re.IGNORECASE)

    # Cut off simulated subsequent user turns, conversational restarts, or re-introductions
    simulated_turns = [
        r'</tool_call>',
        r'<tool_call>',
        r'</tool_response>',
        r'<tool_response>',
        r'\n(?:User|Human|Question):\s*',
        r'\n###\s*(?:User|Human|Prompt)',
        r'<\|im_start\|>',
        r'<\|im_end\|>',
    ]
    for sim in simulated_turns:
        m = re.search(sim, text, re.IGNORECASE)
        if m and m.start() > 20: # ensure we don't cut off immediate start
            text = text[:m.start()]

    # Cut off duplicate self re-introduction if repeated
    reintro_match = re.search(r'\nI\'m Ari\b', text[20:], re.IGNORECASE)
    if reintro_match:
        text = text[:20 + reintro_match.start()]

    # Strip unnecessary outer ```markdown ... ``` wrappers so tables and prose render directly as styled rich content
    text = re.sub(r'^```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$', r'\1', text.strip(), flags=re.IGNORECASE)

    # Handle HTML formatting:
    # 1. If it's a full raw HTML document/webpage and not fenced, wrap it in an html code block
    if "```" not in text and re.search(r'<!DOCTYPE\s+html|<html\b', text, re.IGNORECASE):
        text = f"```html\n{text.strip()}\n```"
    else:
        # 2. Outside fenced code blocks, convert any stray conversational HTML tags (e.g. <h3>, <ol>, <li>, <div>)
        # into clean Markdown so recipes and guides render as beautiful rich text rather than code boxes
        parts = re.split(r'(```[\s\S]*?```)', text)
        converted_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Outside code blocks
                # Convert headings <h1> to <h6> -> Markdown # to ######
                for level in range(6, 0, -1):
                    part = re.sub(rf'<h{level}\b[^>]*>(.*?)</h{level}>', r'\n\n' + ('#' * level) + r' \1\n\n', part, flags=re.IGNORECASE | re.DOTALL)
                # Convert bold and italic tags
                part = re.sub(r'<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>', r'**\1**', part, flags=re.IGNORECASE | re.DOTALL)
                part = re.sub(r'<(?:em|i)\b[^>]*>(.*?)</(?:em|i)>', r'*\1*', part, flags=re.IGNORECASE | re.DOTALL)
                # Convert list items <li>item</li> -> - item
                part = re.sub(r'<li\b[^>]*>(.*?)</li>', r'\n- \1', part, flags=re.IGNORECASE | re.DOTALL)
                # Strip structural HTML wrapper tags so markdown flows naturally
                part = re.sub(r'</?(?:ul|ol|div|span|section|article|p|header|footer|nav|main)\b[^>]*>', '\n', part, flags=re.IGNORECASE)
                # Convert <br> to newline
                part = re.sub(r'<br\s*/?>', '\n', part, flags=re.IGNORECASE)
                # Normalize multiple newlines
                part = re.sub(r'\n{3,}', '\n\n', part)
            converted_parts.append(part)
        text = ''.join(converted_parts)

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
                    "models": list_available_models()
                }
    except Exception:
        pass

    # 2. Check Ollama service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                return {
                    "online": True,
                    "engine": "ollama",
                    "models": list_available_models()
                }
    except Exception:
        pass

    # 3. Not running, but check if standalone files are present
    has_exe = get_engine_executable() is not None
    has_model = get_model_file() is not None
    return {
        "online": False,
        "engine": "standalone" if (has_exe and has_model) else "none",
        "models": list_available_models() if (has_exe and has_model) else []
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
    "</tool_call>",
    "<tool_call>",
    "</tool_response>",
    "<tool_response>",
    "\nUser:",
    "\nHuman:",
    "\nQuestion:",
    "\n### User",
    "\n### Human",
    "\n<|im_start|>user",
    "\n<|im_start|>assistant",
]

async def stream_chat_completion(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.35,
    reasoning_mode: bool = False,
    max_tokens: int = 2048
) -> AsyncGenerator[str, None]:
    """Streams chat tokens from Standalone llama-server (OpenAI format) or Ollama with circuit breakers."""
    # Ensure standalone engine is ready and serving the requested model (3B or 1.5B)
    standalone_ready = await ensure_standalone_engine(model)
    health = await check_engine_health()
    engine_type = "standalone" if standalone_ready else health.get("engine", "standalone")

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
        async for item in _stream_standalone(processed_messages, temperature, max_tokens):
            yield item
    else:
        # Stream from Ollama
        async for item in _stream_ollama(processed_messages, model, temperature):
            yield item

async def _stream_standalone(
    messages: List[Dict[str, str]],
    temperature: float = 0.35,
    max_tokens: int = 2048
) -> AsyncGenerator[str, None]:
    """Streams tokens via OpenAI SSE format from standalone llama-server."""
    url = f"{STANDALONE_BASE_URL}/v1/chat/completions"
    payload = {
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.9,
        "top_k": 40,
        "repeat_penalty": 1.05,
        "max_tokens": max_tokens,
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
                                # Clean control characters (preserve UTF-8, emojis, accented chars)
                                clean_tok = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]+', '', content)
                                accumulated += clean_tok

                                for stop_tok in STOP_WORDS:
                                    if stop_tok.lower() in accumulated.lower():
                                        logger.info(f"Stream circuit break: stop_word '{stop_tok}'")
                                        yield json.dumps({"done": True, "token": "", "circuit_break": True, "reason": f"stop_word:{stop_tok}"}) + "\n"
                                        return

                                if detect_simulated_turn(accumulated):
                                    logger.info("Stream circuit break: simulated_turn")
                                    yield json.dumps({"done": True, "token": "", "circuit_break": True, "reason": "simulated_turn"}) + "\n"
                                    return

                                rep_pat = detect_repetition(accumulated, threshold=3)
                                if rep_pat:
                                    logger.info(f"Stream circuit break: repetition '{rep_pat[:30]}'")
                                    yield json.dumps({"done": True, "circuit_break": True, "reason": f"repetition:{rep_pat}"}) + "\n"
                                    return

                                yield json.dumps({"token": clean_tok, "done": done}) + "\n"

                            if done:
                                logger.info(f"Stream finished normally: finish_reason={finish_reason}")
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
