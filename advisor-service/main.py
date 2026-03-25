"""
Advisor Service — Proactive suggestion generation service
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient

# Add parent directory to path for shared module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm_router import LLMRouter

from suggestion_engine import SuggestionEngine
from web_researcher import WebResearcher
from notifier import Notifier

# ─── Configuration ──────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
ADVISOR_CRON = os.getenv("ADVISOR_CRON", "0 8 * * *")  # Daily at 8 AM
ADVISOR_TIMEZONE = os.getenv("ADVISOR_TIMEZONE", "Asia/Seoul")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "memory_chunks")
DEFAULT_USER = os.getenv("DEFAULT_USER_ID", "default")
WEB_RESEARCH_ENABLED = os.getenv("WEB_RESEARCH_ENABLED", "false").lower() == "true"

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
suggestion_engine: SuggestionEngine = None
web_researcher: WebResearcher = None
notifier: Notifier = None

last_generation_status = {
    "last_run": None,
    "status": "not_started",
    "message": "",
    "suggestions_count": 0,
}


# ─── Lifecycle ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global db_pool, qdrant_client, llm_router, scheduler
    global suggestion_engine, web_researcher, notifier

    # Startup
    logger.info("🚀 Starting Advisor Service...")

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
    suggestion_engine = SuggestionEngine(
        db_pool, qdrant_client, llm_router, COLLECTION_NAME
    )
    web_researcher = WebResearcher()
    notifier = Notifier()
    logger.info("✓ Services initialized")

    # Scheduler
    scheduler = AsyncIOScheduler(timezone=ADVISOR_TIMEZONE)
    scheduler.add_job(
        scheduled_generation,
        trigger=CronTrigger.from_crontab(ADVISOR_CRON),
        id="advisor_generation",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"✓ Scheduler started (cron: {ADVISOR_CRON}, tz: {ADVISOR_TIMEZONE})")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Advisor Service...")
    if scheduler:
        scheduler.shutdown()
    if db_pool:
        await db_pool.close()
    if qdrant_client:
        await qdrant_client.close()
    logger.info("✓ Cleanup complete")


app = FastAPI(
    title="Advisor Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Scheduled Job ──────────────────────────────────────

async def scheduled_generation():
    """Periodic suggestion generation job."""
    logger.info("⏰ Scheduled advisor generation started")
    last_generation_status["last_run"] = datetime.utcnow().isoformat()
    last_generation_status["status"] = "running"

    try:
        suggestions = await run_generation(
            DEFAULT_USER,
            web_research=WEB_RESEARCH_ENABLED,
            notify=True,
        )

        last_generation_status["status"] = "success"
        last_generation_status["message"] = "Suggestions generated successfully"
        last_generation_status["suggestions_count"] = len(suggestions)

        logger.info(f"✅ Scheduled generation complete: {len(suggestions)} suggestions")

    except Exception as e:
        logger.error(f"❌ Scheduled generation failed: {e}", exc_info=True)
        last_generation_status["status"] = "error"
        last_generation_status["message"] = str(e)
        last_generation_status["suggestions_count"] = 0

        # Notify about error
        await notifier.send_status("error", str(e))


async def run_generation(
    user_id: str,
    web_research: bool = False,
    notify: bool = False,
) -> list:
    """Core generation logic."""
    # Step 1: Generate suggestions
    suggestions = await suggestion_engine.generate_suggestions(
        user_id=user_id,
        max_interests=5,
        include_trends=True,
    )

    if not suggestions:
        logger.warning(f"No suggestions generated for user={user_id}")
        return []

    # Step 2: Optional web research
    if web_research and web_researcher.enabled:
        try:
            # Extract top interest topics
            async with db_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT topic FROM interests
                    WHERE user_id = $1
                    ORDER BY intensity DESC
                    LIMIT 3
                    """,
                    user_id,
                )
            topics = [r["topic"] for r in rows]

            if topics:
                trends_text = web_researcher.search_trends(topics, max_results=3)
                if trends_text:
                    logger.info(f"Web research results included: {len(trends_text)} chars")
                    # Could append to suggestions metadata here
        except Exception as e:
            logger.warning(f"Web research failed: {e}")

    # Step 3: Send notifications
    if notify:
        await notifier.send_suggestions(suggestions)

    return suggestions


# ─── API Endpoints ──────────────────────────────────────

class GenerateRequest(BaseModel):
    user_id: str = DEFAULT_USER
    web_research: bool = False
    notify: bool = False


class GenerateResponse(BaseModel):
    status: str
    user_id: str
    suggestions_count: int
    suggestions: list


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "advisor",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/api/v1/advisor/generate", response_model=GenerateResponse)
async def trigger_generation(req: GenerateRequest):
    """Manually trigger suggestion generation."""
    logger.info(
        f"Manual generation triggered for user={req.user_id}, "
        f"web_research={req.web_research}, notify={req.notify}"
    )

    try:
        suggestions = await run_generation(
            req.user_id,
            web_research=req.web_research,
            notify=req.notify,
        )

        return GenerateResponse(
            status="success",
            user_id=req.user_id,
            suggestions_count=len(suggestions),
            suggestions=suggestions,
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/advisor/status")
async def get_status():
    """Get last generation status."""
    return {
        "status": "ok",
        "last_generation": last_generation_status,
        "scheduler": {
            "running": scheduler.running if scheduler else False,
            "cron": ADVISOR_CRON,
            "timezone": ADVISOR_TIMEZONE,
        },
        "features": {
            "web_research": WEB_RESEARCH_ENABLED,
            "notifier": notifier.webhook_enabled or notifier.telegram_enabled,
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
