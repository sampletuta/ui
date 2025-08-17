import numpy as np
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def validate_embedding(embedding: np.ndarray) -> bool:
    """
    Validate that an embedding vector is properly formatted
    
    Args:
        embedding: numpy array to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not isinstance(embedding, np.ndarray):
            return False
        
        if embedding.ndim != 1:
            return False
        
        if embedding.shape[0] != 512:  # InsightFace embedding dimension
            return False
        
        if not np.isfinite(embedding).all():
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Embedding validation failed: {e}")
        return False

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    Normalize embedding vector to unit length
    
    Args:
        embedding: numpy array to normalize
        
    Returns:
        Normalized embedding vector
    """
    try:
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return embedding
        return embedding / norm
    except Exception as e:
        logger.error(f"Embedding normalization failed: {e}")
        return embedding

def calculate_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two embeddings
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Similarity score between 0 and 1
    """
    try:
        if not validate_embedding(embedding1) or not validate_embedding(embedding2):
            return 0.0
        
        # Normalize embeddings
        norm1 = normalize_embedding(embedding1)
        norm2 = normalize_embedding(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(norm1, norm2)
        return float(max(0.0, min(1.0, similarity)))
        
    except Exception as e:
        logger.error(f"Similarity calculation failed: {e}")
        return 0.0

def batch_similarity_search(query_embedding: np.ndarray, 
                          candidate_embeddings: List[np.ndarray],
                          threshold: float = 0.6) -> List[Dict]:
    """
    Perform batch similarity search against a list of candidate embeddings
    
    Args:
        query_embedding: Query embedding vector
        candidate_embeddings: List of candidate embedding vectors
        threshold: Minimum similarity threshold
        
    Returns:
        List of similar embeddings with scores and indices
    """
    try:
        if not validate_embedding(query_embedding):
            return []
        
        results = []
        for i, candidate in enumerate(candidate_embeddings):
            if not validate_embedding(candidate):
                continue
                
            similarity = calculate_similarity(query_embedding, candidate)
            if similarity >= threshold:
                results.append({
                    'index': i,
                    'similarity_score': similarity,
                    'embedding': candidate
                })
        
        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results
        
    except Exception as e:
        logger.error(f"Batch similarity search failed: {e}")
        return []

def embedding_to_list(embedding: np.ndarray) -> List[float]:
    """
    Convert numpy embedding to list for JSON serialization
    
    Args:
        embedding: numpy array to convert
        
    Returns:
        List representation of embedding
    """
    try:
        if validate_embedding(embedding):
            return embedding.tolist()
        return []
    except Exception as e:
        logger.error(f"Embedding to list conversion failed: {e}")
        return []

def list_to_embedding(embedding_list: List[float]) -> Optional[np.ndarray]:
    """
    Convert list back to numpy embedding
    
    Args:
        embedding_list: List representation of embedding
        
    Returns:
        numpy array or None if conversion fails
    """
    try:
        embedding = np.array(embedding_list, dtype=np.float32)
        if validate_embedding(embedding):
            return embedding
        return None
    except Exception as e:
        logger.error(f"List to embedding conversion failed: {e}")
        return None
