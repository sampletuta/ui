import numpy as np
from face_ai.services.re_ranking import ReRanker


def test_reranker_basic():
    query = np.array([1.0, 0.0, 0.0])
    candidates = [
        {'target_id': 'a', 'embedding': [1.0, 0.0, 0.0], 'source': 'uploaded_image'},
        {'target_id': 'b', 'embedding': [0.0, 1.0, 0.0], 'source': 'other'},
    ]

    reranker = ReRanker(weights={"embed": 0.9, "metadata": 0.1}, metadata_boosts={"same_source": 0.2})
    ranked = reranker.rerank(query, candidates, query_meta={'source': 'uploaded_image'})

    # Expect candidate 'a' to be ranked above 'b'
    assert ranked[0]['target_id'] == 'a'
    assert ranked[0]['final_score'] >= ranked[1]['final_score']



