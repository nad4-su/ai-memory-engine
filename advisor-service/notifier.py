"""
Notifier — Send notifications via Webhook or Telegram
"""
import logging
import os
from typing import Dict, List, Any

import httpx

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self):
        self.webhook_url = os.getenv("NOTIFY_WEBHOOK", "")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        self.webhook_enabled = bool(self.webhook_url)
        self.telegram_enabled = bool(self.telegram_token and self.telegram_chat_id)

        if not self.webhook_enabled and not self.telegram_enabled:
            logger.warning("No notification method configured (webhook/telegram)")
        else:
            logger.info(
                f"✓ Notifier enabled: webhook={self.webhook_enabled}, "
                f"telegram={self.telegram_enabled}"
            )

    async def send_suggestions(self, suggestions: List[Dict[str, Any]]) -> None:
        """Send suggestions via configured notification channels."""
        if not suggestions:
            logger.info("No suggestions to send")
            return

        # Format message
        message = self._format_message(suggestions)

        # Send to webhook
        if self.webhook_enabled:
            await self._send_webhook(message, suggestions)

        # Send to Telegram
        if self.telegram_enabled:
            await self._send_telegram(message)

    def _format_message(self, suggestions: List[Dict[str, Any]]) -> str:
        """Format suggestions as readable message."""
        lines = ["🔔 새로운 제안이 도착했습니다!\n"]

        for i, sug in enumerate(suggestions, 1):
            title = sug.get("title", "제목 없음")
            content = sug.get("content", "")
            category = sug.get("category", "일반")
            steps = sug.get("actionable_steps", [])

            lines.append(f"{i}. [{category}] {title}")
            lines.append(f"   {content}")

            if steps:
                lines.append("   실행 단계:")
                for step in steps[:3]:  # Limit to 3 steps
                    lines.append(f"   • {step}")

            lines.append("")  # Empty line between suggestions

        return "\n".join(lines)

    async def _send_webhook(
        self, message: str, suggestions: List[Dict[str, Any]]
    ) -> None:
        """Send to webhook endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        "message": message,
                        "suggestions": suggestions,
                        "type": "advisor_suggestions",
                    },
                )
                response.raise_for_status()
                logger.info(f"✓ Webhook notification sent: {response.status_code}")
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")

    async def _send_telegram(self, message: str) -> None:
        """Send to Telegram Bot API."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.telegram_chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                    },
                )
                response.raise_for_status()
                logger.info(f"✓ Telegram notification sent")
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")

    async def send_status(self, status: str, details: str = "") -> None:
        """Send status update (errors, warnings)."""
        message = f"⚠️ Advisor Service Status: {status}\n\n{details}"

        if self.telegram_enabled:
            await self._send_telegram(message)
        elif self.webhook_enabled:
            await self._send_webhook(message, [])
