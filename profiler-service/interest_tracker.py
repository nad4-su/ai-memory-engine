"""
Interest Tracker — Calculate interest intensity and trends
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import asyncpg

logger = logging.getLogger(__name__)


class InterestTracker:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def calculate_intensity(
        self, user_id: str, topic: str, days: int = 7
    ) -> float:
        """
        Calculate interest intensity based on mention frequency and recency.
        Formula: intensity = (mention_count × recency_weight) / max_value
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT created_at
                FROM ingest_log
                WHERE user_id = $1
                  AND created_at >= $2
                  AND (content ILIKE $3 OR metadata::text ILIKE $3)
                ORDER BY created_at DESC
                """,
                user_id,
                cutoff,
                f"%{topic}%",
            )

        if not rows:
            return 0.0

        # Recency weighting
        now = datetime.utcnow()
        total_weight = 0.0
        for row in rows:
            created = row["created_at"]
            days_ago = (now - created).days
            # Decay formula: today=1.0, 1day=0.9, 2days=0.81, ..., 7days≈0.3
            recency_weight = 0.9 ** days_ago
            total_weight += recency_weight

        # Normalize to 0~1 range (assuming max 20 mentions with full recency = max)
        max_possible = 20.0
        intensity = min(total_weight / max_possible, 1.0)

        logger.debug(f"Intensity for '{topic}': {intensity:.3f} ({len(rows)} mentions)")
        return intensity

    async def detect_trends(
        self, user_id: str
    ) -> List[Dict[str, str]]:
        """
        Compare this week vs last week to detect rising/falling/stable/new interests.
        Returns: [{topic, direction, reason}]
        """
        this_week_start = datetime.utcnow() - timedelta(days=7)
        last_week_start = datetime.utcnow() - timedelta(days=14)

        async with self.db.acquire() as conn:
            # Get topics from interests table
            topics_rows = await conn.fetch(
                "SELECT topic FROM interests WHERE user_id = $1",
                user_id,
            )

        topics = [r["topic"] for r in topics_rows]
        if not topics:
            return []

        trends = []
        for topic in topics:
            this_week = await self._count_mentions(
                user_id, topic, this_week_start, datetime.utcnow()
            )
            last_week = await self._count_mentions(
                user_id, topic, last_week_start, this_week_start
            )

            direction, reason = self._classify_trend(this_week, last_week)
            trends.append({
                "topic": topic,
                "direction": direction,
                "reason": reason,
            })

        logger.info(f"Detected {len(trends)} trends for user={user_id}")
        return trends

    async def _count_mentions(
        self, user_id: str, topic: str, start: datetime, end: datetime
    ) -> int:
        """Count how many times a topic was mentioned in a time range."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) as cnt
                FROM ingest_log
                WHERE user_id = $1
                  AND created_at >= $2
                  AND created_at < $3
                  AND (content ILIKE $4 OR metadata::text ILIKE $4)
                """,
                user_id,
                start,
                end,
                f"%{topic}%",
            )
        return row["cnt"] if row else 0

    @staticmethod
    def _classify_trend(this_week: int, last_week: int) -> Tuple[str, str]:
        """
        Classify trend direction.
        Returns: (direction, reason)
        """
        if last_week == 0 and this_week > 0:
            return ("new", f"새로 등장 (이번 주 {this_week}회)")
        elif last_week == 0 and this_week == 0:
            return ("stable", "언급 없음")
        elif this_week > last_week * 1.5:
            return ("rising", f"증가 추세 (지난주 {last_week}회 → 이번주 {this_week}회)")
        elif this_week < last_week * 0.5:
            return ("falling", f"감소 추세 (지난주 {last_week}회 → 이번주 {this_week}회)")
        else:
            return ("stable", f"유지 (이번주 {this_week}회)")
