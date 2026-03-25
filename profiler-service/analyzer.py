"""
Analyzer — LLM-based conversation/activity analysis
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import asyncpg
from qdrant_client import AsyncQdrantClient

from shared.llm_router import LLMRouter, Message

logger = logging.getLogger(__name__)


class Analyzer:
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        qdrant_client: AsyncQdrantClient,
        llm_router: LLMRouter,
        collection_name: str = "memory_chunks",
    ):
        self.db = db_pool
        self.qdrant = qdrant_client
        self.llm = llm_router
        self.collection_name = collection_name

    async def analyze_recent_activity(
        self, user_id: str = "default", days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze user activity from the past N days.
        Returns: {interests, patterns, trends}
        """
        logger.info(f"Analyzing activity for user={user_id}, days={days}")

        # 1. Fetch recent logs from PostgreSQL
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT content, metadata, created_at
                FROM ingest_log
                WHERE user_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
                LIMIT 200
                """,
                user_id,
                cutoff,
            )

        if not rows:
            logger.warning(f"No activity found for user={user_id}")
            return {"interests": [], "patterns": {}, "trends": []}

        # 2. Fetch recent chunks from Qdrant (if available)
        qdrant_chunks = []
        try:
            search_result = await self.qdrant.scroll(
                collection_name=self.collection_name,
                limit=100,
                with_payload=True,
                with_vectors=False,
            )
            # search_result is (records, next_offset)
            records, _ = search_result
            for rec in records:
                payload = rec.payload or {}
                if payload.get("user_id") == user_id:
                    qdrant_chunks.append(payload.get("text", ""))
        except Exception as e:
            logger.warning(f"Failed to fetch Qdrant chunks: {e}")

        # 3. Build context for LLM
        activity_text = self._build_activity_context(rows, qdrant_chunks)

        # 4. Call LLM for analysis
        system_prompt = """당신은 사용자 행동 분석가입니다.
아래 대화/활동 기록을 분석하여 JSON으로 반환하세요.

출력 형식:
{
  "interests": [
    {"topic": "주제명", "category": "카테고리", "intensity": 0.8, "evidence": "근거"}
  ],
  "patterns": {
    "active_hours": [9, 10, 14, 20],
    "preferred_topics": ["주제1", "주제2"],
    "decision_style": "빠른결정|숙고형|위임형"
  },
  "trends": [
    {"topic": "주제", "direction": "rising|falling|stable|new", "reason": "이유"}
  ]
}

- interests: 사용자가 관심 있는 주제 목록 (intensity는 0~1 사이)
- patterns: 활동 패턴 (시간대, 선호 주제, 의사결정 스타일)
- trends: 관심사 변화 추세

JSON만 반환하세요. 다른 텍스트는 포함하지 마세요."""

        user_prompt = f"분석 대상 활동 기록:\n\n{activity_text}"

        try:
            response = await self.llm.chat(
                messages=[
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            # Parse JSON from response
            result = self._parse_json_response(response.content)
            logger.info(f"Analysis complete: {len(result.get('interests', []))} interests found")
            return result

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            raise

    def _build_activity_context(
        self, db_rows: List[asyncpg.Record], qdrant_chunks: List[str]
    ) -> str:
        """Build activity context text for LLM."""
        parts = ["### PostgreSQL 수집 로그:"]
        for row in db_rows[:50]:  # Limit to avoid token overflow
            content = row["content"]
            created = row["created_at"].strftime("%Y-%m-%d %H:%M")
            parts.append(f"[{created}] {content[:200]}")

        if qdrant_chunks:
            parts.append("\n### Qdrant 대화 청크:")
            for chunk in qdrant_chunks[:30]:
                parts.append(f"- {chunk[:150]}")

        return "\n".join(parts)

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response (may have markdown wrapping)."""
        content = content.strip()
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nContent: {content[:500]}")
            # Return empty structure
            return {"interests": [], "patterns": {}, "trends": []}

    async def save_analysis_result(
        self, user_id: str, result: Dict[str, Any]
    ) -> None:
        """Save analysis result to PostgreSQL."""
        async with self.db.acquire() as conn:
            # Update user_profile
            await conn.execute(
                """
                INSERT INTO user_profile (user_id, profile_data, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET profile_data = $2, updated_at = NOW()
                """,
                user_id,
                json.dumps(result),
            )

            # Insert/update interests
            interests = result.get("interests", [])
            for interest in interests:
                await conn.execute(
                    """
                    INSERT INTO interests (user_id, topic, category, intensity, evidence, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                    ON CONFLICT (user_id, topic) DO UPDATE
                    SET intensity = $4, evidence = $5, category = $3, updated_at = NOW()
                    """,
                    user_id,
                    interest.get("topic", ""),
                    interest.get("category", "general"),
                    interest.get("intensity", 0.5),
                    interest.get("evidence", ""),
                )

        logger.info(f"Saved {len(interests)} interests for user={user_id}")
