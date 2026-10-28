"""Hybrid ranking using Reciprocal Rank Fusion (RRF).

Scores from FTS5 (bm25) and cosine similarity live on different scales, so
they are never summed directly. RRF combines *ranks*, which makes the fusion
deterministic and independent of scale.
"""
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass
class RankedItem:
    chunk_id: str
    rank: int


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]],
    k: int = 60,
    weights: Sequence[float] | None = None,
) -> List[tuple[str, float]]:
    """Fuse several ranked id lists into one deterministic ranking.

    Args:
        rankings: Each element is an ordered list of chunk ids (best first).
        k: RRF smoothing constant. Higher k flattens the contribution of top ranks.
        weights: Optional per-list weight, same length as `rankings`.

    Returns:
        List of (chunk_id, score) sorted by score descending, then by the best
        rank and finally by chunk_id so results are fully deterministic.
    """
    if weights is None:
        weights = [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights must match the number of rankings")

    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    first_seen: dict[str, int] = {}

    for list_index, ranking in enumerate(rankings):
        weight = weights[list_index]
        for position, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight / (k + position)
            best_rank[chunk_id] = min(best_rank.get(chunk_id, position), position)
            if chunk_id not in first_seen:
                first_seen[chunk_id] = position

    ordered = sorted(
        scores.items(),
        key=lambda item: (-item[1], best_rank[item[0]], first_seen[item[0]], item[0]),
    )
    return ordered


def deduplicate_by_document(
    ranked: Iterable[tuple[str, float]],
    chunk_to_document: dict[str, str],
    max_per_document: int = 2,
) -> List[tuple[str, float]]:
    """Limit how many chunks from a single document can dominate results."""
    counts: dict[str, int] = {}
    kept: List[tuple[str, float]] = []
    for chunk_id, score in ranked:
        document_id = chunk_to_document.get(chunk_id)
        if document_id is not None:
            used = counts.get(document_id, 0)
            if used >= max_per_document:
                continue
            counts[document_id] = used + 1
        kept.append((chunk_id, score))
    return kept
