"""
Obsidian vault source parser
Parses markdown documents
"""
import re
from typing import Any, Dict, List


class ObsidianParser:
    """Parse Obsidian markdown documents"""
    
    @staticmethod
    def parse(content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Obsidian markdown content
        
        Args:
            content: Markdown text
            metadata: Additional metadata
        
        Returns:
            List of document items (one per document)
        """
        # Extract frontmatter if exists
        frontmatter = {}
        body = content
        
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                # Parse YAML frontmatter (simple key: value)
                for line in parts[1].strip().split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        frontmatter[key.strip()] = value.strip()
                body = parts[2].strip()
        
        # Extract title (first # heading or filename)
        title = metadata.get("filename", "Untitled")
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        
        # Remove markdown syntax for cleaner text
        clean_text = ObsidianParser._clean_markdown(body)
        
        return [{
            "text": clean_text,
            "metadata": {
                **metadata,
                "source_type": "obsidian",
                "title": title,
                "frontmatter": frontmatter,
            }
        }]
    
    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Clean markdown syntax for better embedding"""
        # Remove code blocks
        text = re.sub(r"```[a-z]*\n.*?```", "", text, flags=re.DOTALL)
        
        # Remove inline code
        text = re.sub(r"`[^`]+`", "", text)
        
        # Remove images
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        
        # Remove links but keep text
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        
        # Remove WikiLinks [[...]]
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        
        # Remove heading markers
        text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)
        
        # Remove bold/italic markers
        text = re.sub(r"(\*\*|__)", "", text)
        text = re.sub(r"(\*|_)", "", text)
        
        # Clean up whitespace
        text = re.sub(r"\n\n+", "\n\n", text)
        text = text.strip()
        
        return text
