"""
Simple vector store implementation for SEMP knowledge base
"""
import os
import pickle
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
import numpy as np
import faiss
from loguru import logger


class SimpleVectorStore:
    """Simple vector store using FAISS for similarity search"""
    
    def __init__(self, dimension: int, storage_path: str):
        self.dimension = dimension
        self.storage_path = Path(storage_path)
        self.metadata_path = self.storage_path.with_suffix('.json')
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self.metadata = []  # Store metadata for each vector
        self.texts = []     # Store original texts
        
        # Load existing data if available
        self._load()
        
        logger.info(f"Vector store initialized with {self.index.ntotal} vectors")
    
    def add_vector(self, vector: np.ndarray, text: str, metadata: Dict[str, Any] = None) -> int:
        """Add a vector to the store with associated text and metadata"""
        # Normalize vector for cosine similarity
        vector = vector.astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        # Add to FAISS index
        vector_2d = vector.reshape(1, -1)
        self.index.add(vector_2d)
        
        # Store metadata and text
        vector_id = len(self.texts)
        self.texts.append(text)
        self.metadata.append(metadata or {})
        
        return vector_id
    
    def search(self, query_vector: np.ndarray, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        if self.index.ntotal == 0:
            return []
        
        # Normalize query vector
        query_vector = query_vector.astype(np.float32)
        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm
        
        # Search FAISS index
        query_2d = query_vector.reshape(1, -1)
        scores, indices = self.index.search(query_2d, min(top_k, self.index.ntotal))
        
        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and score >= score_threshold:  # Valid index and meets threshold
                results.append({
                    'text': self.texts[idx],
                    'score': float(score),
                    'metadata': self.metadata[idx],
                    'index': int(idx)
                })
        
        return results
    
    def get_all_vectors(self) -> List[Dict[str, Any]]:
        """Get all vectors with their metadata"""
        results = []
        for i in range(len(self.texts)):
            results.append({
                'text': self.texts[i],
                'metadata': self.metadata[i],
                'index': i
            })
        return results
    
    def save(self) -> None:
        """Save the vector store to disk"""
        try:
            # Create directory if it doesn't exist
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(self.storage_path))
            
            # Save metadata and texts
            data = {
                'metadata': self.metadata,
                'texts': self.texts,
                'dimension': self.dimension
            }
            
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Vector store saved to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            raise
    
    def _load(self) -> None:
        """Load the vector store from disk"""
        try:
            # Load FAISS index if it exists
            if self.storage_path.exists():
                self.index = faiss.read_index(str(self.storage_path))
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            # Load metadata and texts if they exist
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.metadata = data.get('metadata', [])
                self.texts = data.get('texts', [])
                
                # Verify dimension consistency
                saved_dimension = data.get('dimension', self.dimension)
                if saved_dimension != self.dimension:
                    logger.warning(f"Dimension mismatch: expected {self.dimension}, got {saved_dimension}")
                
                logger.info(f"Loaded {len(self.texts)} text entries")
            
        except Exception as e:
            logger.warning(f"Could not load existing vector store: {e}")
            # Initialize fresh if loading fails
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            self.texts = []
    
    def clear(self) -> None:
        """Clear all vectors from the store"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self.texts = []
        logger.info("Vector store cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'storage_size_bytes': self.storage_path.stat().st_size if self.storage_path.exists() else 0,
            'metadata_entries': len(self.metadata),
            'text_entries': len(self.texts)
        }