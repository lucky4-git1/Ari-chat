# Ari Chat 🤖✨
### Standalone, Zero-Setup AI Companion (Runs 100% Locally Without Ollama)

**Ari Chat** is a standalone, private, zero-dependency personal AI companion built for **laptops, desktops, and mobile devices (4 GB–8 GB+ RAM)**. It provides the polish, warmth, and reasoning of modern ChatGPT without requiring Ollama, Docker, or complex developer environments.

---

## 🌟 Highlights

- **⚡ 100% Standalone & Embedded**: Powered by an embedded native neural engine with AVX2 acceleration. Runs models directly on CPU or GPU without Ollama or external daemons.
- **🧠 Multi-Model Intelligence**:
  - **Ari 3B Assistant (Recommended)**: Master GPT-level conversational companion with deep reasoning, coding capabilities, and empathetic dialogue.
  - **Ari 1.5B Assistant (Updated)**: Ultra-fast, lightweight paraphraser and everyday assistant fine-tuned on editorial multi-sentence corpora.
- **💻 Ultra-Low RAM Footprint**: Optimized `Q4_K_M` quantization (~940 MB for 1.5B, ~1.8 GB for 3B). Sub-second token latency on standard CPU hardware.
- **🛑 Active Stop Generation**: ChatGPT-style instant generation cancellation via active square stop button or `Escape` key with graceful partial response preservation.
- **🎨 Modern Architectural UI**: Distraction-free dark and light canvas themes, custom vector typography, and syntax-highlighted code blocks with copy-to-clipboard.
- **📱 Seamless Cross-Device LAN & Android**:
  - Open `http://<your-pc-ip>:8000` from any Android phone, iPhone, iPad, Mac, or Linux computer on your local Wi-Fi.
  - Run natively on Android hardware using the included `start-android.sh` in Termux!
- **🌐 Real-Time Web Grounding**: Live DuckDuckGo web results citation with one click.
- **🧠 Persistent Memory**: Automatically extracts your name, preferences, and background into local SQLite storage across sessions.

---

## 🚀 Quickstart

### 1. Windows (1-Click Launch)
Double-click `AriChat.exe` or `start.bat`:
```cmd
start.bat
```
- Automatically verifies environment and downloads engine if needed.
- Loads Ari 3B or Ari 1.5B.
- Opens **http://localhost:8000** in your default browser.
- Displays your mobile Wi-Fi URL (e.g., `http://192.168.x.x:8000`) for instant phone access.

### 2. macOS & Linux
```bash
chmod +x start.sh
./start.sh
```
Automatically detects your architecture (Apple Silicon ARM64, Intel x86_64, or Linux x86_64), provisions the matching engine binary, and launches the application.

### 3. Android (Native via Termux)
```bash
chmod +x start-android.sh
./start-android.sh
```
Or simply run Ari Chat on your PC/laptop and open `http://<PC-IP>:8000` on your Android phone's Chrome/Firefox browser!

---

## 📦 Model Selection & Switching

Ari Chat includes a live model dropdown in the top navigation bar:
- **Ari 3B Assistant**: Master model for advanced reasoning, creative writing, and complex multi-turn coding.
- **Ari 1.5B Assistant**: Ultra-fast model for quick answers, rewriting, and paraphrasing.

Switching models in the UI immediately rebinds the embedded neural engine in real time with zero downtime.

---

## 📁 Repository Structure

```
ari-chat-app/
├── app/
│   ├── main.py              # FastAPI application & lifecycle manager
│   ├── core/config.py       # Configuration & model directories
│   ├── db/database.py       # SQLite connection & ORM models
│   ├── services/
│   │   ├── engine_service.py# Standalone embedded engine controller & model switcher
│   │   ├── search_service.py# Real-time web search grounding
│   │   └── memory_service.py# Long-term memory extraction
│   └── api/
│       ├── chat_routes.py   # SSE streaming, token generation, abort handler
│       └── models_routes.py # Model discovery & switching endpoints
├── bin/                     # Native standalone engine binaries (llama-server)
├── models/                  # GGUF models (ari_assistant_1.5b.gguf, ari_assistant_3b.gguf)
├── static/                  # Responsive web frontend (Tailwind, FontAwesome, Highlight.js)
├── run_app.py               # Standalone runner entrypoint
├── setup_engine.py          # Cross-platform engine & model provisioner
├── start.bat                # Windows 1-click launcher
├── start.sh                 # Linux / macOS 1-click launcher
├── start-android.sh         # Android Termux launcher
└── requirements.txt         # Minimal Python dependencies
```

---

## 📄 License
MIT License. Open source and free for personal and commercial use.
