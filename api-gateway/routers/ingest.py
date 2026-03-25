"""
Data ingestion endpoints
"""
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class IngestRequest(BaseModel):
    source: str  # conversation, obsidian, bookmark
    content: str
    metadata: Dict[str, Any] = {}


class BatchIngestRequest(BaseModel):
    source: str
    items: List[Dict[str, Any]]


@router.post("/ingest")
async def ingest_data(request: Request, data: IngestRequest):
    """
    Ingest single data item
    
    Body:
    {
        "source": "conversation|obsidian|bookmark",
        "content": "text content",
        "metadata": {"key": "value"}
    }
    """
    ingest_url = os.getenv("INGEST_SERVICE_URL", "http://ingest-service:8001")
    
    try:
        resp = await request.app.state.http.post(
            f"{ingest_url}/ingest",
            json={
                "source": data.source,
                "content": data.content,
                "metadata": data.metadata,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        result = resp.json()
        
        # Log to database
        async with request.app.state.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO ingest_log (source, item_count, vector_count, status)
                VALUES ($1, $2, $3, $4)
            """, data.source, 1, result.get("chunks_created", 0), "success")
        
        return result
    
    except Exception as e:
        # Log error
        async with request.app.state.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO ingest_log (source, item_count, vector_count, status, error_message)
                VALUES ($1, $2, $3, $4, $5)
            """, data.source, 1, 0, "error", str(e))
        
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/batch")
async def ingest_batch(request: Request, data: BatchIngestRequest):
    """
    Batch ingest multiple items
    
    Body:
    {
        "source": "conversation|obsidian|bookmark",
        "items": [
            {"content": "...", "metadata": {...}},
            ...
        ]
    }
    """
    ingest_url = os.getenv("INGEST_SERVICE_URL", "http://ingest-service:8001")
    
    try:
        resp = await request.app.state.http.post(
            f"{ingest_url}/ingest/batch",
            json={"source": data.source, "items": data.items},
            timeout=300.0,  # Longer timeout for batch
        )
        resp.raise_for_status()
        result = resp.json()
        
        # Log to database
        async with request.app.state.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO ingest_log (source, item_count, vector_count, status)
                VALUES ($1, $2, $3, $4)
            """, data.source, len(data.items), result.get("chunks_created", 0), "success")
        
        return result
    
    except Exception as e:
        # Log error
        async with request.app.state.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO ingest_log (source, item_count, vector_count, status, error_message)
                VALUES ($1, $2, $3, $4, $5)
            """, data.source, len(data.items), 0, "error", str(e))
        
        raise HTTPException(status_code=500, detail=f"Batch ingestion failed: {str(e)}")
