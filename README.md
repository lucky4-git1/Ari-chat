# Ari Chat 🤖✨
### Production-Ready ChatGPT Alternative Powered by Ari-LLM 1.5B

**Ari Chat** is a complete, self-hosted, private AI conversational web platform built natively on top of **Ari-LLM 1.5B** (`ari-assistant`). It gives you the full power and polish of modern ChatGPT—with complete privacy, cross-session memory, live web search, deep reasoning, and multi-user accounts.

---

## 🌟 Highlights

- **Native Ari-LLM 1.5B Engine**: Powered by your local model via Ollama with 4-thread CPU optimization and 2048-token context window.
- **🎨 Modern Dark & Light Mode UI**: Beautiful ChatGPT-inspired responsive interface with one-click theme switcher, localStorage persistence, and syntax highlighting.
- **🧠 Cross-Session Long-Term Memory**: Ari remembers your name, preferences, past projects, and instructions across completely separate chat sessions.
- **🌐 Real-Time Web Search**: Ground responses in live DuckDuckGo web results and cite clickable sources with one click.
- **🤔 Deep Reasoning Mode**: Step-by-step thinking process displayed in collapsible badges before the final answer.
- **👥 Multi-User Accounts**: User registration, login, secure PBKDF2 password hashing, and private chat histories.
- **⚡ Real-Time Streaming**: Server-Sent Events (SSE) token streaming, markdown rendering, syntax-highlighted code blocks, and 1-click copy buttons.
- **🚀 1-Click Launch**: Zero complex setup, runs natively on Windows, Linux, and macOS.

---

## 🚀 Quickstart

### Windows
Double-click `start.bat` or run:
```cmd
start.bat
```

### Linux / macOS
```bash
chmod +x start.sh
./start.sh
```

### Manual Launch
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser at **[http://localhost:8000](http://localhost:8000)**.

---

## 📁 Project Architecture

```
ari-chat-app/
├── app/
│   ├── main.py              # FastAPI server entrypoint
│   ├── core/
│   │   ├── config.py        # Configuration, Ollama & JWT settings
│   │   └── security.py      # PBKDF2 hashing & HMAC-SHA256 tokens
│   ├── db/
│   │   ├── database.py      # SQLite connection & engine
│   │   └── models.py        # User, Conversation, Message, Memory
│   ├── services/
│   │   ├── ollama_service.py# Streaming client for Ari-LLM
│   │   ├── search_service.py# Live DuckDuckGo search integration
│   │   └── memory_service.py# Long-term memory extraction & retrieval
│   └── api/
│       ├── auth_routes.py   # Register, Login, Me endpoints
│       ├── chat_routes.py   # Conversations & SSE message streaming
│       └── memory_routes.py # Manage user memories
├── static/
│   ├── index.html           # Full responsive ChatGPT-style UI
│   ├── css/style.css        # Dark theme, glassmorphic styling
│   └── js/
│       ├── api.js           # REST API client
│       └── app.js           # Chat controller & streaming UI logic
├── start.bat                # Windows 1-click launcher
├── start.sh                 # Linux/Mac 1-click launcher
└── requirements.txt
```
