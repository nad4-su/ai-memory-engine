"""
Ingest Service — Data ingestion and vectorization
"""
import asyncpg
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient

# Add shared to path
sys.path.insert(0, "/app/shared")
from llm_router import LLMRouter

from chunker import TextChunker
from vectorizer import Vectorizer
from sources.conversation import ConversationParser
from sources.obsidian import ObsidianParser
from sources.bookmark import BookmarkParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db_pool: Optional[asyncpg.Pool] = None
qdrant_client: Optional[QdrantClient] = None
llm_router: Optional[LLMRouter] = None
vectorizer: Optional[Vectorizer] = None
chunker: Optional[TextChunker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global db_pool, qdrant_client, llm_router, vectorizer, chunker
    
    # Startup
    logger.info("Starting Ingest Service...")
    
    # Database
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/ai_memory")
    try:
        db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        logger.info("✓ Database connected")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise
    
    # Qdrant
    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    try:
        qdrant_client = QdrantClient(url=qdrant_url)
        qdrant_client.get_collections()
        logger.info("✓ Qdrant connected")
    except Exception as e:
        logger.error(f"✗ Qdrant connection failed: {e}")
        raise
    
    # LLM Router
    try:
        llm_router = LLMRouter.from_env()
        logger.info("✓ LLM Router initialized")
    except Exception as e:
        logger.error(f"✗ LLM Router initialization failed: {e}")
        raise
    
    # Vectorizer
    vectorizer = Vectorizer(qdrant_client, llm_router)
    logger.info("✓ Vectorizer initialized")
    
    # Chunker
    chunk_size = int(os.getenv("CHUNK_SIZE", "512"))
    overlap = int(os.getenv("CHUNK_OVERLAP", "128"))
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    logger.info(f"✓ Chunker initialized (size={chunk_size}, overlap={overlap})")
    
    app.state.db = db_pool
    app.state.qdrant = qdrant_client
    app.state.llm = llm_router
    app.state.vectorizer = vectorizer
    app.state.chunker = chunker
    
    logger.info("Ingest Service ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Ingest Service...")
    if db_pool:
        await db_pool.close()
    logger.info("Ingest Service stopped")


app = FastAPI(
    title="AI Memory Ingest Service",
    description="Data ingestion and vectorization service",
    version="1.0.0",
    lifespan=lifespan,
)


class IngestRequest(BaseModel):
    source: str  # conversation, obsidian, bookmark
    content: str
    metadata: Dict[str, Any] = {}


class BatchIngestRequest(BaseModel):
    source: str
    items: List[Dict[str, Any]]


# Source parser mapping
SOURCE_PARSERS = {
    "conversation": ConversationParser,
    "obsidian": ObsidianParser,
    "bookmark": BookmarkParser,
}

# Collection name mapping
COLLECTION_MAP = {
    "conversation": "conversations",
    "obsidian": "documents",
    "bookmark": "bookmarks",
}


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "service": "ingest-service"}


@app.post("/ingest")
async def ingest_single(request: IngestRequest):
    """
    Ingest single item
    """
    # Get parser
    parser_class = SOURCE_PARSERS.get(request.source)
    if not parser_class:
        raise HTTPException(status_code=400, detail=f"Unknown source: {request.source}")
    
    # Parse content
    items = parser_class.parse(request.content, request.metadata)
    
    if not items:
        return {"status": "success", "chunks_created": 0, "message": "No content to ingest"}
    
    # Process each item
    total_chunks = 0
    collection_name = COLLECTION_MAP.get(request.source, "documents")
    
    for item in items:
        text = item["text"]
        metadata = item["metadata"]
        
        # Chunk text
        chunks = chunker.chunk(text)
        
        # Vectorize and store
        count = await vectorizer.vectorize_and_store(
            collection_name=collection_name,
            chunks=chunks,
            metadata=metadata,
        )
        total_chunks += count
    
    # Log to database
    try:
        import json
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ingest_log (user_id, source, content, metadata, item_count, vector_count, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, "default", request.source, request.content[:5000], 
                json.dumps(request.metadata), len(items), total_chunks, "success")
    except Exception as e:
        logger.warning(f"Failed to log ingest: {e}")
    
    return {
        "status": "success",
        "source": request.source,
        "items_processed": len(items),
        "chunks_created": total_chunks,
        "collection": collection_name,
    }


@app.post("/ingest/batch")
async def ingest_batch(request: BatchIngestRequest):
    """
    Ingest batch of items
    """
    parser_class = SOURCE_PARSERS.get(request.source)
    if not parser_class:
        raise HTTPException(status_code=400, detail=f"Unknown source: {request.source}")
    
    total_chunks = 0
    collection_name = COLLECTION_MAP.get(request.source, "documents")
    
    for batch_item in request.items:
        content = batch_item.get("content", "")
        metadata = batch_item.get("metadata", {})
        
        if not content:
            continue
        
        # Parse
        items = parser_class.parse(content, metadata)
        
        # Process each
        for item in items:
            text = item["text"]
            item_metadata = item["metadata"]
            
            # Chunk
            chunks = chunker.chunk(text)
            
            # Vectorize and store
            count = await vectorizer.vectorize_and_store(
                collection_name=collection_name,
                chunks=chunks,
                metadata=item_metadata,
            )
            total_chunks += count
    
    return {
        "status": "success",
        "source": request.source,
        "items_processed": len(request.items),
        "chunks_created": total_chunks,
        "collection": collection_name,
    }
