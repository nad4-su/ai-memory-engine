"""
Text chunker with token-based splitting
Splits text into chunks of ~512 tokens with 128 token overlap
"""
import tiktoken
from typing import List


class TextChunker:
    def __init__(self, chunk_size: int = 512, overlap: int = 128):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target size in tokens
            overlap: Overlap size in tokens
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
    
    def chunk(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        # Encode text to tokens
        tokens = self.encoding.encode(text)
        
        # If text is shorter than chunk size, return as-is
        if len(tokens) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Get chunk
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start forward by (chunk_size - overlap)
            start += (self.chunk_size - self.overlap)
            
            # Break if we're past the end
            if end >= len(tokens):
                break
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
