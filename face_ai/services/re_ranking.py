"""Re-ranking utilities for face search.

Provides a ReRanker class that scores Milvus candidates using embedding
similarity and optional metadata boosts. Designed to be simple and
configurable via settings.
"""
from typing import List, Dict, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None:
        return 0.0
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


class ReRanker:
    """Simple re-ranker combining embedding similarity with metadata boosts.

    Usage:
        reranker = ReRanker(weights={"embed": 0.8, "metadata": 0.2})
        ranked = reranker.rerank(query_embedding, candidates)
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None, metadata_boosts: Optional[Dict[str, float]] = None):
        # Default weights (embedding dominates)
        self.weights = weights or {"embed": 0.85, "metadata": 0.15}
        # Example metadata boost map (e.g. prefer same source/camera)
        self.metadata_boosts = metadata_boosts or {"same_source": 0.1}

    def _metadata_score(self, candidate: Dict, query_meta: Optional[Dict]) -> float:
        if not query_meta:
            return 0.0
        score = 0.0
        try:
            # Example: if source/camera matches, add boost
            if 'source' in candidate and 'source' in query_meta and candidate['source'] == query_meta['source']:
                score += self.metadata_boosts.get('same_source', 0.0)
            # Add more metadata heuristics here as needed
        except Exception as e:
            logger.debug(f"metadata scoring error: {e}")
        return float(score)

    def rerank(self, query_embedding: np.ndarray, candidates: List[Dict], query_meta: Optional[Dict] = None) -> List[Dict]:
        """Return candidates re-ordered with score breakdown.

        Each returned dict will include additional keys:
            - final_score: combined score used for sorting
            - embed_score: cosine similarity
            - metadata_score: additive metadata boost
        """
        ranked = []
        for c in candidates:
            try:
                embed_vec = c.get('embedding')  # optional: Milvus may not return embedding by default
                # If embedding vector not present, rely on similarity field if provided
                if embed_vec is not None:
                    embed_score = _cosine_similarity(query_embedding, np.array(embed_vec))
                else:
                    embed_score = float(c.get('similarity_score', 0.0))

                metadata_score = self._metadata_score(c, query_meta)

                final = self.weights.get('embed', 0.85) * embed_score + self.weights.get('metadata', 0.15) * metadata_score

                ranked.append({**c, 'final_score': final, 'embed_score': embed_score, 'metadata_score': metadata_score})
            except Exception as e:
                logger.exception(f"Failed to score candidate {c.get('target_id')}: {e}")
                ranked.append({**c, 'final_score': 0.0, 'embed_score': 0.0, 'metadata_score': 0.0})

        # Sort descending by final_score
        ranked_sorted = sorted(ranked, key=lambda x: x.get('final_score', 0.0), reverse=True)
        return ranked_sorted



