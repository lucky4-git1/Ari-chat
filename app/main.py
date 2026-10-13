import os
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
from app.services.ollama_service import check_ollama_health

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

# Initialize Database on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Mount API Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(memory_router)

@app.get("/api/health")
async def health_check():
    ollama_status = await check_ollama_health()
    return {
        "status": "healthy",
        "app": PROJECT_NAME,
        "version": VERSION,
        "ollama": ollama_status
    }

# Static assets and SPA mounting
STATIC_DIR = BASE_DIR / "static"
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
