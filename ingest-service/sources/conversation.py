"""
Conversation log source parser
Parses JSON/JSONL conversation logs
"""
import json
from typing import Any, Dict, List


class ConversationParser:
    """Parse conversation logs (JSON/JSONL format)"""
    
    @staticmethod
    def parse(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse conversation content
        
        Args:
            content: Raw conversation data (JSON or JSONL)
            metadata: Additional metadata
        
        Returns:
            List of conversation items
        """
        items = []
        
        # Try JSON first
        try:
            data = json.loads(content)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = [data]
        except json.JSONDecodeError:
            # Try JSONL (one JSON object per line)
            for line in content.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    items.append(item)
                except json.JSONDecodeError:
                    continue
        
        # Extract text from each item
        results = []
        for i, item in enumerate(items):
            text = ConversationParser._extract_text(item)
            if text:
                results.append({
                    "text": text,
                    "metadata": {
                        **metadata,
                        "item_index": i,
                        "source_type": "conversation",
                        "original_item": item,
                    }
                })
        
        return results
    
    @staticmethod
    def _extract_text(item: Dict[str, Any]) -> str:
        """Extract text from conversation item"""
        # Common fields
        for field in ["content", "message", "text", "body"]:
            if field in item and isinstance(item[field], str):
                return item[field]
        
        # If item has 'messages' array
        if "messages" in item and isinstance(item["messages"], list):
            texts = []
            for msg in item["messages"]:
                if isinstance(msg, dict):
                    for field in ["content", "message", "text"]:
                        if field in msg:
                            texts.append(str(msg[field]))
                elif isinstance(msg, str):
                    texts.append(msg)
            return "\n".join(texts)
        
        # Fallback: JSON dump
        return json.dumps(item, ensure_ascii=False)
