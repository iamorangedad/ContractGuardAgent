import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router as contracts_router
from app.rag.db import init_db
from app.config import get_config

config = get_config()

logging.basicConfig(
    level=getattr(logging, config.get("logging", {}).get("level", "INFO")),
    format=config.get("logging", {}).get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logger = logging.getLogger(__name__)

app = FastAPI(title="ContractGuardAgent - 法务合同对比系统")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

app.include_router(contracts_router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting ContractGuardAgent...")
    init_db()
    logger.info("Database initialized")

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_path)

@app.get("/compare")
async def compare_page():
    compare_path = os.path.join(STATIC_DIR, "compare.html")
    return FileResponse(compare_path)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "ContractGuardAgent is running"}

if __name__ == "__main__":
    import uvicorn
    app_config = config.get("app", {})
    uvicorn.run(
        app, 
        host=app_config.get("host", "0.0.0.0"), 
        port=app_config.get("port", 8000)
    )
