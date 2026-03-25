"""
Profiler Service — User profile analysis service
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

# Add parent directory to path for shared module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm_router import LLMRouter

from analyzer import Analyzer
from interest_tracker import InterestTracker
from pattern_detector import PatternDetector

# ─── Configuration ──────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
PROFILER_CRON = os.getenv("PROFILER_CRON", "0 0 * * *")  # Daily at midnight
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "memory_chunks")
DEFAULT_USER = os.getenv("DEFAULT_USER_ID", "default")

# Validate environment
if not DATABASE_URL:
    logger.error("DATABASE_URL is required")
    sys.exit(1)

if not os.getenv("LLM_PROVIDER") or not os.getenv("LLM_API_KEY"):
    logger.error("LLM_PROVIDER and LLM_API_KEY are required")
    sys.exit(1)

# ─── Global State ───────────────────────────────────────

db_pool: asyncpg.Pool = None
qdrant_client: AsyncQdrantClient = None
llm_router: LLMRouter = None
scheduler: AsyncIOScheduler = None
analyzer: Analyzer = None
interest_tracker: InterestTracker = None
pattern_detector: PatternDetector = None

last_analysis_status = {
    "last_run": None,
    "status": "not_started",
    "message": "",
}


# ─── Lifecycle ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global db_pool, qdrant_client, llm_router, scheduler
    global analyzer, interest_tracker, pattern_detector

    # Startup
    logger.info("🚀 Starting Profiler Service...")

    # Database
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    logger.info("✓ Database pool created")

    # Qdrant
    qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
    logger.info(f"✓ Qdrant client connected: {QDRANT_URL}")

    # LLM Router
    llm_router = LLMRouter.from_env()
    logger.info("✓ LLM Router initialized")

    # Services
    analyzer = Analyzer(db_pool, qdrant_client, llm_router, COLLECTION_NAME)
    interest_tracker = InterestTracker(db_pool)
    pattern_detector = PatternDetector(db_pool)
    logger.info("✓ Services initialized")

    # Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scheduled_analysis,
        trigger=CronTrigger.from_crontab(PROFILER_CRON),
        id="profiler_analysis",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"✓ Scheduler started (cron: {PROFILER_CRON})")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Profiler Service...")
    if scheduler:
        scheduler.shutdown()
    if db_pool:
        await db_pool.close()
    if qdrant_client:
        await qdrant_client.close()
    logger.info("✓ Cleanup complete")


app = FastAPI(
    title="Profiler Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Scheduled Job ──────────────────────────────────────

async def scheduled_analysis():
    """Periodic analysis job."""
    logger.info("⏰ Scheduled profiler analysis started")
    last_analysis_status["last_run"] = datetime.utcnow().isoformat()
    last_analysis_status["status"] = "running"

    try:
        await run_analysis(DEFAULT_USER)
        last_analysis_status["status"] = "success"
        last_analysis_status["message"] = "Analysis completed successfully"
        logger.info("✅ Scheduled analysis complete")
    except Exception as e:
        logger.error(f"❌ Scheduled analysis failed: {e}", exc_info=True)
        last_analysis_status["status"] = "error"
        last_analysis_status["message"] = str(e)


async def run_analysis(user_id: str, days: int = 7):
    """Core analysis logic."""
    # Step 1: Analyze with LLM
    result = await analyzer.analyze_recent_activity(user_id, days)

    # Step 2: Calculate intensities
    for interest in result.get("interests", []):
        topic = interest["topic"]
        intensity = await interest_tracker.calculate_intensity(user_id, topic, days)
        interest["intensity"] = intensity

    # Step 3: Detect trends
    trends = await interest_tracker.detect_trends(user_id)
    result["trends"] = trends

    # Step 4: Detect patterns
    patterns = await pattern_detector.detect_patterns(user_id, days=30)
    result["patterns"] = patterns

    # Step 5: Save to database
    await analyzer.save_analysis_result(user_id, result)

    return result


# ─── API Endpoints ──────────────────────────────────────

class AnalyzeRequest(BaseModel):
    user_id: str = DEFAULT_USER
    days: int = 7


class AnalyzeResponse(BaseModel):
    status: str
    user_id: str
    result: dict


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "profiler",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/v1/profiler/analyze", response_model=AnalyzeResponse)
async def trigger_analysis(req: AnalyzeRequest):
    """Manually trigger profile analysis."""
    logger.info(f"Manual analysis triggered for user={req.user_id}, days={req.days}")

    try:
        result = await run_analysis(req.user_id, req.days)
        return AnalyzeResponse(
            status="success",
            user_id=req.user_id,
            result=result,
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/profiler/status")
async def get_status():
    """Get last analysis status."""
    return {
        "status": "ok",
        "last_analysis": last_analysis_status,
        "scheduler": {
            "running": scheduler.running if scheduler else False,
            "cron": PROFILER_CRON,
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
