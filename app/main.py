import logging
import os
import urllib.error
import urllib.request
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as contracts_router
from app.config import get_config
from app.rag.db import init_db

config = get_config()

logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format=config.get("logging", {}).get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
)

logger = logging.getLogger(__name__)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ContractGuardAgent...")
    init_db()
    logger.info("Database initialized")
    yield


app = FastAPI(title="ContractGuardAgent - 法务合同对比系统", lifespan=lifespan)
app.include_router(contracts_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def llm_status() -> dict:
    llm = get_config().get("llm", {})
    if not llm.get("use_llm"):
        return {"enabled": False, "status": "disabled"}

    provider = llm.get("provider", "ollama")
    if provider == "openai":
        if os.getenv("OPENAI_API_KEY"):
            return {"enabled": True, "provider": "openai", "status": "configured"}
        return {"enabled": True, "provider": "openai", "status": "missing_api_key"}

    if provider == "ollama":
        url = llm.get("base_url", "http://localhost:11434").rstrip("/") + "/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                ok = response.status == 200
            return {
                "enabled": True,
                "provider": "ollama",
                "status": "ok" if ok else "unavailable",
            }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return {"enabled": True, "provider": "ollama", "status": "unavailable"}

    return {"enabled": True, "provider": provider, "status": "unknown"}


@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/compare")
async def compare_page():
    return FileResponse(os.path.join(STATIC_DIR, "compare.html"))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "llm": llm_status()}


@app.get("/ready")
async def readiness_check():
    llm = llm_status()
    ready = (not llm.get("enabled")) or llm.get("status") in ("ok", "configured", "disabled")
    body = {"status": "ready" if ready else "not_ready", "llm": llm}
    if not ready:
        return JSONResponse(status_code=503, content=body)
    return body


if __name__ == "__main__":
    import uvicorn

    app_config = config.get("app", {})
    uvicorn.run(
        "app.main:app",
        host=app_config.get("host", "0.0.0.0"),
        port=app_config.get("port", 8000),
    )
