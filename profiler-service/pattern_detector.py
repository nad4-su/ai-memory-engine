"""
Pattern Detector — Detect behavioral patterns (time, day, decision style)
"""
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import asyncpg

logger = logging.getLogger(__name__)


class PatternDetector:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def detect_patterns(self, user_id: str, days: int = 30) -> Dict:
        """
        Detect user behavioral patterns:
        - active_hours: List of hours (0-23) when user is most active
        - preferred_topics: Most frequently mentioned topics
        - decision_style: quick|deliberate|delegating
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT content, metadata, created_at
                FROM ingest_log
                WHERE user_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
                """,
                user_id,
                cutoff,
            )

        if not rows:
            logger.warning(f"No data to detect patterns for user={user_id}")
            return {
                "active_hours": [],
                "preferred_topics": [],
                "decision_style": "unknown",
            }

        # Active hours
        hour_counter = Counter()
        for row in rows:
            hour = row["created_at"].hour
            hour_counter[hour] += 1

        # Top 4 active hours
        active_hours = [h for h, _ in hour_counter.most_common(4)]

        # Day of week pattern
        dow_counter = Counter()
        for row in rows:
            dow = row["created_at"].weekday()  # 0=Monday, 6=Sunday
            dow_counter[dow] += 1

        # Preferred topics (extract from existing interests table)
        preferred_topics = await self._get_preferred_topics(user_id)

        # Decision style
        decision_style = await self._detect_decision_style(user_id, rows)

        result = {
            "active_hours": sorted(active_hours),
            "preferred_topics": preferred_topics,
            "decision_style": decision_style,
            "day_of_week_distribution": dict(dow_counter),
        }

        logger.info(f"Detected patterns: {result}")
        return result

    async def _get_preferred_topics(self, user_id: str, limit: int = 5) -> List[str]:
        """Get top N topics from interests table."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT topic
                FROM interests
                WHERE user_id = $1
                ORDER BY intensity DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [r["topic"] for r in rows]

    async def _detect_decision_style(
        self, user_id: str, activity_rows: List
    ) -> str:
        """
        Detect decision-making style based on:
        - Quick: Fast responses, action-oriented keywords
        - Deliberate: Long pauses, research/analysis keywords
        - Delegating: Questions, seeking opinions
        """
        # Simple heuristic based on content keywords
        quick_keywords = ["바로", "즉시", "지금", "빨리", "실행", "확정"]
        deliberate_keywords = ["검토", "분석", "생각", "고민", "연구", "시간"]
        delegate_keywords = ["추천", "의견", "어떻게", "도와줘", "부탁", "확인"]

        quick_count = 0
        deliberate_count = 0
        delegate_count = 0

        for row in activity_rows[:100]:  # Limit to recent 100
            content = row["content"].lower()
            if any(kw in content for kw in quick_keywords):
                quick_count += 1
            if any(kw in content for kw in deliberate_keywords):
                deliberate_count += 1
            if any(kw in content for kw in delegate_keywords):
                delegate_count += 1

        # Determine dominant style
        scores = {
            "빠른결정": quick_count,
            "숙고형": deliberate_count,
            "위임형": delegate_count,
        }

        if max(scores.values()) == 0:
            return "unknown"

        return max(scores, key=scores.get)
