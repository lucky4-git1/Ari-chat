# Forwarding module for backward compatibility
from app.services.engine_service import (
    check_engine_health,
    check_ollama_health,
    stream_chat_completion,
    detect_repetition,
    strip_repeating_suffix,
    clean_response_text,
    start_standalone_engine,
    stop_standalone_engine,
    STOP_WORDS
)

__all__ = [
    "check_engine_health",
    "check_ollama_health",
    "stream_chat_completion",
    "detect_repetition",
    "strip_repeating_suffix",
    "clean_response_text",
    "start_standalone_engine",
    "stop_standalone_engine",
    "STOP_WORDS"
]
