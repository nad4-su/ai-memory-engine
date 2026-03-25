"""
Vector search endpoints
"""
import os
import sys
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

# Add shared to path for LLM router
sys.path.insert(0, "/app/shared")
from llm_router import LLMRouter, Message

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    filters: Dict[str, Any] = {}
    collections: Optional[List[str]] = None  # None = search all


@router.post("/search")
async def vector_search(request: Request, data: SearchRequest):
    """
    Vector search across collections
    
    Body:
    {
        "query": "search query text",
        "limit": 10,
        "filters": {"category": "tech"},
        "collections": ["conversations", "documents"]  // optional
    }
    """
    try:
        # Get embedding for query
        llm_router = LLMRouter.from_env()
        embedding_resp = await llm_router.embed(data.query)
        query_vector = embedding_resp.embedding
        
        # Determine collections to search
        collections = data.collections or ["conversations", "documents", "bookmarks"]
        
        all_results = []
        
        for collection_name in collections:
            try:
                # Check if collection exists
                collections_info = request.app.state.qdrant.get_collections()
                collection_names = [c.name for c in collections_info.collections]
                
                if collection_name not in collection_names:
                    continue
                
                # Search in collection
                search_result = request.app.state.qdrant.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=data.limit,
                    query_filter=data.filters if data.filters else None,
                )
                
                # Format results
                for point in search_result:
                    all_results.append({
                        "collection": collection_name,
                        "score": point.score,
                        "id": point.id,
                        "payload": point.payload,
                    })
            
            except Exception as e:
                # Log but continue with other collections
                print(f"Error searching {collection_name}: {e}")
                continue
        
        # Sort by score (highest first)
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Limit total results
        all_results = all_results[:data.limit]
        
        return {
            "query": data.query,
            "results": all_results,
            "count": len(all_results),
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
