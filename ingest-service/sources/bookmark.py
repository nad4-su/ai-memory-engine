"""
Bookmark source parser
Parses bookmark data (e.g., from Karakeep API)
"""
import json
from typing import Any, Dict, List


class BookmarkParser:
    """Parse bookmark data"""
    
    @staticmethod
    def parse(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse bookmark content
        
        Args:
            content: Raw bookmark data (JSON)
            metadata: Additional metadata
        
        Returns:
            List of bookmark items
        """
        items = []
        
        # Try JSON
        try:
            data = json.loads(content)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = [data]
        except json.JSONDecodeError:
            # Fallback: treat as plain text URL list
            for line in content.strip().split("\n"):
                if line.strip():
                    items.append({"url": line.strip()})
        
        # Extract text from each bookmark
        results = []
        for i, item in enumerate(items):
            text = BookmarkParser._extract_text(item)
            if text:
                results.append({
                    "text": text,
                    "metadata": {
                        **metadata,
                        "item_index": i,
                        "source_type": "bookmark",
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "tags": item.get("tags", []),
                    }
                })
        
        return results
    
    @staticmethod
    def _extract_text(item: Dict[str, Any]) -> str:
        """Extract text from bookmark item"""
        parts = []
        
        # Title
        if "title" in item:
            parts.append(item["title"])
        
        # Description or notes
        for field in ["description", "note", "notes", "excerpt"]:
            if field in item and item[field]:
                parts.append(str(item[field]))
        
        # Tags (as comma-separated)
        if "tags" in item and isinstance(item["tags"], list):
            parts.append("Tags: " + ", ".join(str(t) for t in item["tags"]))
        
        # URL (for context)
        if "url" in item:
            parts.append(f"URL: {item['url']}")
        
        return "\n".join(parts) if parts else item.get("url", "")
