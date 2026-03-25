"""
Suggestion Engine — Generate actionable suggestions based on user profile
"""
import json
import logging
from typing import Any, Dict, List, Optional

import asyncpg
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from shared.llm_router import LLMRouter, Message

logger = logging.getLogger(__name__)


class SuggestionEngine:
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

    async def generate_suggestions(
        self,
        user_id: str = "default",
        max_interests: int = 5,
        include_trends: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate suggestions based on user profile and interests.
        Returns: [{title, content, category, actionable_steps, related_interest}]
        """
        logger.info(f"Generating suggestions for user={user_id}")

        # 1. Fetch user profile
        profile = await self._fetch_profile(user_id)
        if not profile:
            logger.warning(f"No profile found for user={user_id}")
            return []

        # 2. Get top interests
        interests = await self._fetch_top_interests(user_id, max_interests)
        if not interests:
            logger.warning(f"No interests found for user={user_id}")
            return []

        # 3. RAG search for each interest
        rag_context = await self._build_rag_context(user_id, interests)

        # 4. Optional: Get trends
        trends_text = ""
        if include_trends:
            trends_text = await self._get_trends_summary(profile)

        # 5. Call LLM to generate suggestions
        suggestions = await self._generate_with_llm(
            profile, interests, rag_context, trends_text
        )

        # 6. Save to database
        await self._save_suggestions(user_id, suggestions)

        logger.info(f"Generated {len(suggestions)} suggestions for user={user_id}")
        return suggestions

    async def _fetch_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile from PostgreSQL."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT profile_data FROM user_profile WHERE user_id = $1",
                user_id,
            )
        if row and row["profile_data"]:
            return row["profile_data"]
        return None

    async def _fetch_top_interests(
        self, user_id: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch top N interests by intensity."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT topic, category, intensity, evidence
                FROM interests
                WHERE user_id = $1
                ORDER BY intensity DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [
            {
                "topic": r["topic"],
                "category": r["category"],
                "intensity": float(r["intensity"]),
                "evidence": r["evidence"],
            }
            for r in rows
        ]

    async def _build_rag_context(
        self, user_id: str, interests: List[Dict[str, Any]]
    ) -> str:
        """Search Qdrant for relevant past records for each interest."""
        context_parts = []

        for interest in interests[:3]:  # Limit to top 3 to avoid token overflow
            topic = interest["topic"]
            try:
                # Search Qdrant using topic as query
                search_results = await self.qdrant.search(
                    collection_name=self.collection_name,
                    query_text=topic,
                    limit=5,
                    with_payload=True,
                )

                if search_results:
                    context_parts.append(f"\n### '{topic}' 관련 기록:")
                    for res in search_results:
                        payload = res.payload or {}
                        text = payload.get("text", "")
                        context_parts.append(f"- {text[:150]}")

            except Exception as e:
                logger.warning(f"RAG search failed for '{topic}': {e}")

        return "\n".join(context_parts)

    def _get_trends_summary(self, profile: Dict[str, Any]) -> str:
        """Extract trends summary from profile."""
        trends = profile.get("trends", [])
        if not trends:
            return ""

        lines = ["### 최근 트렌드:"]
        for trend in trends[:5]:
            topic = trend.get("topic", "")
            direction = trend.get("direction", "")
            reason = trend.get("reason", "")
            lines.append(f"- {topic}: {direction} ({reason})")

        return "\n".join(lines)

    async def _generate_with_llm(
        self,
        profile: Dict[str, Any],
        interests: List[Dict[str, Any]],
        rag_context: str,
        trends_text: str,
    ) -> List[Dict[str, Any]]:
        """Generate suggestions using LLM."""
        system_prompt = """당신은 개인 비즈니스 어드바이저입니다.
사용자의 프로필과 관심사를 기반으로 실행 가능한 제안을 생성하세요.

출력 형식 (JSON):
{
  "suggestions": [
    {
      "title": "제안 제목",
      "content": "제안 내용 (2-3문장)",
      "category": "카테고리",
      "actionable_steps": ["단계1", "단계2", "단계3"],
      "related_interest": "관련 관심사"
    }
  ]
}

조건:
- 각 제안은 구체적이고 실행 가능해야 함
- 사용자의 관심사 및 패턴에 맞춰야 함
- 최소 3개, 최대 5개의 제안 생성
- actionable_steps는 구체적인 행동 단계 (3-5개)

JSON만 반환하세요."""

        user_prompt = f"""# 사용자 프로필
{json.dumps(profile, ensure_ascii=False, indent=2)}

# TOP 관심사
{json.dumps(interests, ensure_ascii=False, indent=2)}

# 관련 기록 (RAG)
{rag_context}

{trends_text}

위 정보를 바탕으로 사용자에게 유용한 제안을 생성해주세요."""

        try:
            response = await self.llm.chat(
                messages=[
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_prompt),
                ],
                temperature=0.7,
                max_tokens=2500,
            )

            # Parse JSON
            result = self._parse_json_response(response.content)
            suggestions = result.get("suggestions", [])

            # Validate structure
            validated = []
            for sug in suggestions:
                if "title" in sug and "content" in sug:
                    validated.append(sug)

            return validated

        except Exception as e:
            logger.error(f"LLM suggestion generation failed: {e}")
            return []

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        content = content.strip()
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
            return {"suggestions": []}

    async def _save_suggestions(
        self, user_id: str, suggestions: List[Dict[str, Any]]
    ) -> None:
        """Save suggestions to PostgreSQL."""
        async with self.db.acquire() as conn:
            for sug in suggestions:
                await conn.execute(
                    """
                    INSERT INTO suggestions (
                        user_id, title, content, category,
                        actionable_steps, related_interest, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    """,
                    user_id,
                    sug.get("title", ""),
                    sug.get("content", ""),
                    sug.get("category", "general"),
                    json.dumps(sug.get("actionable_steps", [])),
                    sug.get("related_interest", ""),
                )

        logger.info(f"Saved {len(suggestions)} suggestions to database")
