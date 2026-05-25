import json
import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager

from mf_faq.orchestrator.service import OrchestratorService

logger = logging.getLogger("mf_faq.ui.api")

# We use a global service instance so models stay loaded in memory
orchestrator_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator_service
    logger.info("Initializing OrchestratorService at startup...")
    orchestrator_service = OrchestratorService()
    yield
    logger.info("Shutting down...")

app = FastAPI(title="Mutual Fund FAQ API", lifespan=lifespan)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        answer = orchestrator_service.ask(request.query)
        return QueryResponse(answer=answer)
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/meta")
async def get_meta():
    """Returns basic corpus metadata."""
    manifest_path = Path("data/index/manifest.json")
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "n_chunks": data.get("n_chunks", 0),
                "built_at": data.get("built_at", "Unknown")
            }
    return {"n_chunks": 0, "built_at": "Unknown"}

# Serve static files from the static directory
static_dir = Path(__file__).parent / "static"
# Ensure directory exists so FastAPI doesn't crash on mount
static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
