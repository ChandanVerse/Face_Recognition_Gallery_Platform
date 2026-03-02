"""
Pinecone database manager - ported from your existing implementation
"""
import time
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any


class PineconeDatabase:
    """Singleton Pinecone database manager"""
    
    _instance = None
    
    def __new__(cls, api_key: str, index_name: str = "face-embeddings-webapp", environment: str = "us-east-1-aws"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, api_key: str, index_name: str = "face-embeddings-webapp", environment: str = "us-east-1-aws"):
        if self._initialized:
            return
            
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.dimension = 512  # InsightFace embedding dimension
        self.index = None
        
        self._setup_index()
        self._initialized = True
    
    def _setup_index(self):
        """Create Pinecone index if it doesn't exist, otherwise connect to existing"""
        try:
            existing_indexes = self.pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                print(f"Creating new Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric='cosine',
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
                
                print("Waiting for index to be ready...")
                while not self.pc.describe_index(self.index_name).status['ready']:
                    time.sleep(1)
            
            self.index = self.pc.Index(self.index_name)
            print(f"[OK] Connected to Pinecone index: {self.index_name}")

        except Exception as e:
            print(f"[ERROR] Error setting up Pinecone index: {e}")
            self.index = None
    
    def upsert_embeddings(self, embeddings_data: List[Dict[str, Any]], batch_size: int = 1000):
        """
        Store face embeddings in Pinecone with batch processing
        
        Args:
            embeddings_data: List of dicts with keys: 'id', 'embedding', 'metadata'
            batch_size: Number of vectors to upload per batch (max 1000)
        """
        if self.index is None:
            print("[ERROR] Pinecone index not available. Cannot upsert embeddings.")
            return
        
        # Prepare vectors (id, embedding, metadata)
        vectors = [
            (item['id'], item['embedding'].tolist(), item['metadata'])
            for item in embeddings_data
        ]
        
        total_vectors = len(vectors)
        print(f"Uploading {total_vectors} embeddings in batches of {batch_size}...")
        
        for i in range(0, total_vectors, batch_size):
            batch = vectors[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_vectors + batch_size - 1) // batch_size
            
            print(f"  Uploading batch {batch_num}/{total_batches} ({len(batch)} vectors)...")
            
            try:
                self.index.upsert(vectors=batch)
                
                if i + batch_size < total_vectors:
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"  [ERROR] Error uploading batch {batch_num}: {e}")
                raise e
        
        print(f"[OK] Successfully uploaded all {total_vectors} embeddings")
    
    def search_similar_faces(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10000,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar faces using cosine similarity

        Args:
            query_embedding: Face embedding to search for (should be raw/normalized from InsightFace)
            top_k: Maximum number of results
            threshold: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            List of matches with metadata and confidence scores

        Note: Pinecone cosine similarity returns values in [-1, 1] where:
            - 1.0 = identical vectors
            - 0.0 = orthogonal vectors
            - -1.0 = opposite vectors
        We transform the raw score to [0, 1] range using: (score + 1.0) / 2.0
        """
        if self.index is None:
            print("[ERROR] Pinecone index not available. Cannot search.")
            return []

        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True
        )

        matches = []
        for match in results['matches']:
            # Transform Pinecone cosine similarity from [-1, 1] to [0, 1] range
            # This ensures consistency with test expectations and provides more intuitive scores
            confidence = (match['score'] + 1.0) / 2.0

            if confidence >= threshold:
                match_data = match['metadata'].copy()
                match_data['confidence'] = confidence
                match_data['pinecone_id'] = match['id']
                matches.append(match_data)

        return matches
    
    def delete_vectors(self, ids: List[str]):
        """Delete specific vectors by ID"""
        if self.index is None:
            print("[ERROR] Pinecone index not available.")
            return

        self.index.delete(ids=ids)
        print(f"[OK] Deleted {len(ids)} vectors")
    
    def delete_all(self):
        """Clear all vectors from the index"""
        if self.index is None:
            print("[ERROR] Pinecone index not available.")
            return

        self.index.delete(delete_all=True)
        print("[OK] Cleared all vectors from Pinecone index")
    
    def get_index_stats(self) -> Dict[str, Any] | None:
        """Get statistics about the current index"""
        if self.index is None:
            print("[ERROR] Pinecone index not available.")
            return None

        try:
            stats = self.index.describe_index_stats()
            return stats
        except Exception as e:
            print(f"[ERROR] Error getting index stats: {e}")
            return None