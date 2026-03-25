"""
API Gateway — AI Memory Engine
Unified entry point for all services
"""
import asyncpg
import httpx
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse

from routers import health, ingest, search, profile, suggestions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global connections
db_pool: Optional[asyncpg.Pool] = None
qdrant_client: Optional[QdrantClient] = None
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global db_pool, qdrant_client, http_client
    
    # Startup
    logger.info("Starting API Gateway...")
    
    # Database connection
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/ai_memory")
    try:
        db_pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        logger.info("✓ Database connected")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        raise
    
    # Qdrant connection
    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    try:
        qdrant_client = QdrantClient(url=qdrant_url)
        # Test connection
        qdrant_client.get_collections()
        logger.info("✓ Qdrant connected")
    except Exception as e:
        logger.error(f"✗ Qdrant connection failed: {e}")
        raise
    
    # HTTP client for internal service calls
    http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("✓ HTTP client initialized")
    
    app.state.db = db_pool
    app.state.qdrant = qdrant_client
    app.state.http = http_client
    
    logger.info("API Gateway ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")
    if db_pool:
        await db_pool.close()
    if http_client:
        await http_client.aclose()
    logger.info("API Gateway stopped")


app = FastAPI(
    title="AI Memory Engine API",
    description="Unified API Gateway for AI Memory services",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingest"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(profile.router, prefix="/api/v1", tags=["Profile"])
app.include_router(suggestions.router, prefix="/api/v1", tags=["Suggestions"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Memory Engine",
        "version": "1.0.0",
        "docs": "/docs",
    }
