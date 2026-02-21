import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router as contracts_router
from app.rag.db import init_db

app = FastAPI(title="ContractGuardAgent - 法务合同对比系统")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

app.include_router(contracts_router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    init_db()

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
