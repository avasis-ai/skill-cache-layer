"""FastAPI server for skill cache proxy."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from skill_cache_layer.semantic_cache import SemanticCache


logger = logging.getLogger(__name__)


class CacheQuery(BaseModel):
    """Request model for cache queries."""

    skill_name: str
    input_text: str


class CacheAdd(BaseModel):
    """Request model for adding cache entries."""

    skill_name: str
    input_text: str
    result: dict | list | str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage cache server lifecycle."""
    logger.info("Skill Cache Layer API starting...")
    yield
    logger.info("Skill Cache Layer API shutting down...")


app = FastAPI(
    title="Skill Cache Layer API",
    description="High-performance semantic cache for agent skills",
    version="0.1.0",
    lifespan=lifespan
)


# Global cache instance
cache_instance: SemanticCache | None = None
cache_path_str = "/tmp/skill_cache_layer_api.pkl"


@app.on_event("startup")
async def startup_event():
    """Initialize cache on startup."""
    global cache_instance
    cache_instance = SemanticCache(cache_path=cache_path_str)
    logger.info(f"Cache initialized at {cache_path_str}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Skill Cache Layer",
        "version": "0.1.0",
        "endpoints": [
            "/api/search",
            "/api/add",
            "/api/stats",
            "/api/clear"
        ]
    }


@app.post("/api/search")
async def search(query: CacheQuery):
    """Search for cached result.

    Args:
        query: CacheQuery with skill_name and input_text

    Returns:
        Cached result if found
    """
    if not cache_instance:
        raise HTTPException(status_code=500, detail="Cache not initialized")

    result = cache_instance.get(query.skill_name, query.input_text)

    if result is None:
        return {"found": False, "result": None}

    return {
        "found": True,
        "result": result
    }


@app.post("/api/add")
async def add_entry(entry: CacheAdd):
    """Add new cache entry.

    Args:
        entry: CacheAdd with skill_name, input_text, and result

    Returns:
        Confirmation with entry details
    """
    if not cache_instance:
        raise HTTPException(status_code=500, detail="Cache not initialized")

    cache_entry = cache_instance.add(
        skill_name=entry.skill_name,
        input_text=entry.input_text,
        result=entry.result
    )

    return {
        "status": "added",
        "skill_name": entry.skill_name,
        "signature": cache_entry.query_hash
    }


@app.get("/api/stats")
async def get_stats():
    """Get cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    if not cache_instance:
        raise HTTPException(status_code=500, detail="Cache not initialized")

    return cache_instance.stats()


@app.post("/api/clear")
async def clear_cache():
    """Clear all cache entries."""
    if not cache_instance:
        raise HTTPException(status_code=500, detail="Cache not initialized")

    cache_instance.clear()
    cache_instance.save()

    return {"status": "cleared"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "skill-cache-layer"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
