"""
Health check endpoints
"""
import os
from fastapi import APIRouter, Request
from qdrant_client.http.exceptions import UnexpectedResponse

router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """
    System health check
    Returns status of DB, Qdrant, and LLM availability
    """
    status = {
        "service": "ai-memory-engine",
        "status": "healthy",
        "components": {}
    }
    
    # Check database
    try:
        async with request.app.state.db.acquire() as conn:
            await conn.fetchval("SELECT 1")
        status["components"]["database"] = "ok"
    except Exception as e:
        status["components"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    # Check Qdrant
    try:
        request.app.state.qdrant.get_collections()
        status["components"]["qdrant"] = "ok"
    except Exception as e:
        status["components"]["qdrant"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    # Check LLM availability (via env vars)
    llm_provider = os.getenv("LLM_PROVIDER", "not_set")
    llm_api_key = os.getenv("LLM_API_KEY", "")
    if llm_provider and llm_api_key:
        status["components"]["llm"] = f"configured: {llm_provider}"
    else:
        status["components"]["llm"] = "not_configured"
    
    # Check Ingest Service
    try:
        ingest_url = os.getenv("INGEST_SERVICE_URL", "http://ingest-service:8001")
        resp = await request.app.state.http.get(f"{ingest_url}/health", timeout=5.0)
        if resp.status_code == 200:
            status["components"]["ingest_service"] = "ok"
        else:
            status["components"]["ingest_service"] = f"status {resp.status_code}"
    except Exception as e:
        status["components"]["ingest_service"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    return status
