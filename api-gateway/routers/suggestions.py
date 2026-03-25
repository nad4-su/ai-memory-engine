"""
Suggestions endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()


class Suggestion(BaseModel):
    id: int
    title: str
    content: str
    category: Optional[str]
    related_interests: List[int]
    feedback: Optional[str]


class FeedbackRequest(BaseModel):
    feedback: str  # good, bad, neutral
    note: Optional[str] = None


@router.get("/suggestions", response_model=List[Suggestion])
async def get_suggestions(
    request: Request,
    category: Optional[str] = None,
    limit: int = 10,
):
    """
    Get today's suggestions
    
    Query params:
    - category: filter by category
    - limit: max number of results
    """
    try:
        async with request.app.state.db.acquire() as conn:
            query = """
                SELECT id, title, content, category, related_interests,
                       source_context, feedback, feedback_note, created_at
                FROM suggestions
                WHERE DATE(created_at) = CURRENT_DATE
            """
            params = []
            
            if category:
                query += " AND category = $1"
                params.append(category)
                query += " ORDER BY created_at DESC LIMIT $2"
                params.append(limit)
            else:
                query += " ORDER BY created_at DESC LIMIT $1"
                params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "content": row["content"],
                    "category": row["category"],
                    "related_interests": row["related_interests"] or [],
                    "feedback": row["feedback"],
                }
                for row in rows
            ]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch suggestions: {str(e)}")


@router.post("/suggestions/{suggestion_id}/feedback")
async def submit_feedback(
    request: Request,
    suggestion_id: int,
    data: FeedbackRequest,
):
    """
    Submit feedback for a suggestion
    
    Body:
    {
        "feedback": "good|bad|neutral",
        "note": "optional comment"
    }
    """
    if data.feedback not in ["good", "bad", "neutral"]:
        raise HTTPException(status_code=400, detail="Invalid feedback value")
    
    try:
        async with request.app.state.db.acquire() as conn:
            # Check if suggestion exists
            exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM suggestions WHERE id = $1)
            """, suggestion_id)
            
            if not exists:
                raise HTTPException(status_code=404, detail="Suggestion not found")
            
            # Update feedback
            await conn.execute("""
                UPDATE suggestions
                SET feedback = $1, feedback_note = $2
                WHERE id = $3
            """, data.feedback, data.note, suggestion_id)
            
            return {
                "suggestion_id": suggestion_id,
                "feedback": data.feedback,
                "note": data.note,
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")
