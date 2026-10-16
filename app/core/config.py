import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_NAME = "Ari Chat"
VERSION = "1.0.0"

# Ollama Engine Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "ari-assistant-3b")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "ari-assistant-1.5b")

# Database Path
DB_PATH = DATA_DIR / "ari_chat.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "ari-super-secret-key-change-in-production-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Web Search
MAX_SEARCH_RESULTS = 4
