# Ari Chat 🤖✨
### Standalone, Zero-Setup AI Companion Powered by Ari-LLM 1.5B

**Ari Chat** is a lightweight, zero-setup personal AI companion designed specifically for **lower-end laptops (4 GB–8 GB RAM, CPU-only)** that gives you the polish, warmth, and intelligence of modern ChatGPT without requiring Ollama, Docker, or any external software installations.

---

## 🌟 Highlights

- **⚡ 100% Standalone & Local**: Powered by an embedded CPU-optimized engine with AVX2 acceleration. Runs directly on your CPU without requiring Ollama or external daemons.
- **💻 Tailored for Low-End Laptops**: Minimal RAM footprint (~1.2 GB total), sub-second token latency, and seamless operation on 4 GB–8 GB RAM systems.
- **🎨 Modern Dark & Light Mode UI**: Distraction-free, architectural companion interface with one-click theme switcher, custom vector logo, and syntax-highlighted code blocks.
- **🧠 ChatGPT-Style Automatic Memory**: Automatically learns your name, preferences, goals, and interests, updating cross-session long-term memory with real-time UI toasts.
- **🌐 Real-Time Web Search**: Ground responses in live DuckDuckGo web results and cite clickable sources with one click.
- **🤔 Deep Reasoning Mode**: Step-by-step thinking process displayed in collapsible badges before the final answer.
- **👥 Multi-User Accounts**: User registration, login, secure PBKDF2 password hashing, and private chat histories.
- **🚀 1-Click Launch**: Double-click `start.bat` and start chatting immediately in your browser.

---

## 🚀 Quickstart

### 1. Windows (1-Click Launch)
Double-click `start.bat` or run:
```cmd
start.bat
```
`start.bat` automatically verifies Python dependencies, downloads the portable standalone engine if needed (~19 MB), loads Ari 1.5B, and opens **http://localhost:8000** in your browser.

### 2. Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### 3. Manual Launch
```bash
pip install -r requirements.txt
python setup_engine.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Then navigate to **[http://localhost:8000](http://localhost:8000)**.

---

## 📁 Project Architecture

```
ari-chat-app/
├── app/
│   ├── main.py              # FastAPI server & engine lifecycle manager
│   ├── core/
│   │   ├── config.py        # Configuration, paths, & security settings
│   │   └── security.py      # PBKDF2 hashing & HMAC-SHA256 tokens
│   ├── db/
│   │   ├── database.py      # SQLite connection & engine
│   │   └── models.py        # User, Conversation, Message, Memory
│   ├── services/
│   │   ├── engine_service.py# Standalone llama-server & Ollama dual engine
│   │   ├── search_service.py# Live DuckDuckGo search integration
│   │   └── memory_service.py# Long-term memory extraction & retrieval
│   └── api/
│       ├── auth_routes.py   # Register, Login, Me endpoints
│       ├── chat_routes.py   # Conversations & SSE message streaming
│       └── memory_routes.py # Manage user memories
├── bin/                     # Standalone portable engine (auto-installed)
├── models/                  # Ari-LLM 1.5B GGUF model checkpoint
├── static/
│   ├── index.html           # Full responsive ChatGPT-style UI
│   ├── css/style.css        # Minimalist, clean dark & light themes
│   ├── img/logo.svg         # Bespoke Ari companion vector logo
│   └── js/
│       ├── api.js           # REST API client
│       └── app.js           # Chat controller, memory toasts & SSE
├── setup_engine.py          # Standalone binary & model setup utility
├── start.bat                # Windows 1-click zero-setup launcher
├── start.sh                 # Linux/Mac 1-click launcher
└── requirements.txt
```

---

## 🧪 Testing & Verification

Run the integration suite:
```bash
python tests/test_integration.py
```
Validates:
1. Database schema & SQLite connectivity.
2. User authentication & JWT issuance.
3. DuckDuckGo live web search grounding.
4. Automatic long-term memory extraction.
5. Local standalone engine connectivity.
