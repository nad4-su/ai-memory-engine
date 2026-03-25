"""
Vectorizer — Generate embeddings and store in Qdrant
"""
import sys
import uuid
from typing import Any, Dict, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Add shared to path
sys.path.insert(0, "/app/shared")
from llm_router import LLMRouter


class Vectorizer:
    def __init__(self, qdrant_client: QdrantClient, llm_router: LLMRouter):
        """
        Initialize vectorizer
        
        Args:
            qdrant_client: Qdrant client instance
            llm_router: LLM router for embeddings
        """
        self.qdrant = qdrant_client
        self.llm = llm_router
        self.embedding_dim = llm_router.get_embedding_dim()
    
    def ensure_collection(self, collection_name: str):
        """
        Ensure collection exists in Qdrant
        Creates if not exists
        """
        try:
            collections = self.qdrant.get_collections()
            existing = [c.name for c in collections.collections]
            
            if collection_name not in existing:
                self.qdrant.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )
                print(f"✓ Created collection: {collection_name}")
        except Exception as e:
            print(f"Error ensuring collection {collection_name}: {e}")
            raise
    
    async def vectorize_and_store(
        self,
        collection_name: str,
        chunks: List[str],
        metadata: Dict[str, Any],
    ) -> int:
        """
        Vectorize text chunks and store in Qdrant
        
        Args:
            collection_name: Target collection
            chunks: List of text chunks
            metadata: Metadata to attach to each point
        
        Returns:
            Number of vectors stored
        """
        if not chunks:
            return 0
        
        # Ensure collection exists
        self.ensure_collection(collection_name)
        
        # Generate embeddings in batch
        embeddings = await self.llm.embed_batch(chunks)
        
        # Prepare points
        points = []
        for i, (chunk, emb_resp) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk,
                "chunk_index": i,
                **metadata,
            }
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb_resp.embedding,
                    payload=payload,
                )
            )
        
        # Upsert to Qdrant
        self.qdrant.upsert(
            collection_name=collection_name,
            points=points,
        )
        
        return len(points)
