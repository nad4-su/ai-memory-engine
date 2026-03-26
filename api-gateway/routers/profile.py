"""
User profile endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter()
PROFILER_URL = "http://profiler-service:8002"


class Interest(BaseModel):
    id: int
    topic: str
    category: Optional[str]
    intensity: float
    mention_count: int
    trend: str


@router.get("/profile")
async def get_profile(request: Request):
    """
    Get user profile
    """
    try:
        async with request.app.state.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, profile_data, updated_at
                FROM user_profile
                ORDER BY id DESC
                LIMIT 1
            """)
            
            if not row:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            return {
                "id": row["id"],
                "profile_data": row["profile_data"],
                "updated_at": row["updated_at"].isoformat(),
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")


@router.get("/profile/interests", response_model=List[Interest])
async def get_interests(
    request: Request,
    category: Optional[str] = None,
    min_intensity: float = 0.0,
    limit: int = 50,
):
    """
    Get user interests
    
    Query params:
    - category: filter by category
    - min_intensity: minimum intensity threshold
    - limit: max number of results
    """
    try:
        async with request.app.state.db.acquire() as conn:
            query = """
                SELECT id, topic, category, intensity, mention_count,
                       first_seen, last_seen, trend, created_at
                FROM interests
                WHERE intensity >= $1
            """
            params = [min_intensity]
            
            if category:
                query += " AND category = $2"
                params.append(category)
                query += " ORDER BY intensity DESC LIMIT $3"
                params.append(limit)
            else:
                query += " ORDER BY intensity DESC LIMIT $2"
                params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    "id": row["id"],
                    "topic": row["topic"],
                    "category": row["category"],
                    "intensity": row["intensity"],
                    "mention_count": row["mention_count"],
                    "trend": row["trend"],
                }
                for row in rows
            ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch interests: {str(e)}")


@router.post("/profiler/analyze")
async def trigger_analysis():
    """Trigger profiler analysis manually"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{PROFILER_URL}/api/v1/profiler/analyze", json={})
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Profiler service error: {str(e)}")


@router.get("/profiler/status")
async def profiler_status():
    """Get profiler status"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{PROFILER_URL}/api/v1/profiler/status")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Profiler service error: {str(e)}")
