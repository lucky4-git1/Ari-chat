import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import PROJECT_NAME, VERSION, BASE_DIR
from app.db.database import init_db
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.memory_routes import router as memory_router
from app.api.model_routes import router as model_router
from app.api.system_routes import router as system_router
from app.services.engine_service import check_engine_health, start_standalone_engine, stop_standalone_engine, get_model_file

app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="Production-ready ChatGPT-style application powered natively by Ari-LLM 1.5B"
)

# Enable CORS for cross-platform/hybrid clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database and auto-start engine on startup
@app.on_event("startup")
def on_startup():
    init_db()
    # Auto-start standalone engine with Ari 3B model (or fallback to 1.5B)
    start_standalone_engine(get_model_file("ari-assistant-3b"))

@app.on_event("shutdown")
def on_shutdown():
    stop_standalone_engine()

# Mount API Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(model_router)
app.include_router(system_router)

@app.get("/api/health")
async def health_check():
    engine_status = await check_engine_health()
    return {
        "status": "healthy",
        "app": PROJECT_NAME,
        "version": VERSION,
        "engine": engine_status,
        "ollama": engine_status  # Backwards compatibility for UI
    }

# Static assets and SPA mounting
STATIC_DIR = BASE_DIR / "static"
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    bundled = Path(sys._MEIPASS) / "static"
    if bundled.exists():
        STATIC_DIR = bundled
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Ari Chat API is running. Static UI not yet deployed."}

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("   Ari Chat: Launching Production Server on http://localhost:8000")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
