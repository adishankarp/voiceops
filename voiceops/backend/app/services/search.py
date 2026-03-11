from __future__ import annotations

from dataclasses import dataclass
import logging
from math import sqrt
from typing import Any, Dict, List, Optional, Protocol, TypedDict

from app.services.embeddings import embed_text
from app.services.storage import list_conversations

logger = logging.getLogger(__name__)


class SearchResult(TypedDict):
    conversation_id: str
    filename: str
    snippet: str
    score: float


class SearchProvider(Protocol):
    def search(self, query: str) -> List[SearchResult]: ...


def _safe_text(value: Any) -> str:
    return str(value) if value is not None else ""


def _score_occurrences(haystack: str, needle: str) -> int:
    if not haystack or not needle:
        return 0
    normalized = " ".join(haystack.lower().split())
    return normalized.count(needle.lower())


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _best_snippet(text: str, query: str, target_len: int = 200) -> str:
    if not text:
        return ""
    lower = text.lower()
    q = query.lower()
    idx = lower.find(q)
    if idx == -1:
        return (text[:target_len] + "…") if len(text) > target_len else text

    half = target_len // 2
    start = max(0, idx - half)
    end = min(len(text), idx + len(query) + half)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


@dataclass(frozen=True)
class KeywordSearchProvider:
    """
    Semantic + keyword search over stored conversation JSON.

    - Primary ranking: cosine similarity between query embedding
      and conversation["embedding"].
    - Fallback: simple keyword scoring when embeddings are
      unavailable.
    """

    def search(self, query: str) -> List[SearchResult]:
        q = (query or "").strip()
        if not q:
            return []
        logger.info("Search started query_length=%s", len(q))

        # Try to compute query embedding once; if it fails, we
        # gracefully fall back to pure keyword search.
        query_embedding: Optional[List[float]] = None
        try:
            query_embedding = embed_text(q)
        except Exception:
            logger.exception("Query embedding failed; falling back to keyword search")
            query_embedding = None
            logger.info("Using keyword-only search")

        results: List[SearchResult] = []
        for conv in list_conversations():
            conversation_id = _safe_text(conv.get("id")).strip()
            filename = _safe_text(conv.get("filename")).strip()

            transcript = _safe_text(conv.get("transcript"))
            insights = conv.get("insights") or {}
            pain_points = insights.get("pain_points") or []
            objections = insights.get("objections") or []
            buying_signals = insights.get("buying_signals") or []

            fields = {
                "transcript": transcript,
                "pain_points": "\n".join(map(_safe_text, pain_points)) if isinstance(pain_points, list) else _safe_text(pain_points),
                "objections": "\n".join(map(_safe_text, objections)) if isinstance(objections, list) else _safe_text(objections),
                "buying_signals": "\n".join(map(_safe_text, buying_signals)) if isinstance(buying_signals, list) else _safe_text(buying_signals),
            }

            keyword_score = sum(_score_occurrences(text, q) for text in fields.values())

            # Semantic score (if we have embeddings)
            semantic_score = 0.0
            if query_embedding:
                emb = conv.get("embedding")
                if isinstance(emb, list) and all(isinstance(x, (int, float)) for x in emb):
                    semantic_score = _cosine_similarity([float(x) for x in emb], query_embedding)

            # If neither semantic nor keyword matches, skip.
            if semantic_score <= 0.0 and keyword_score <= 0:
                continue

            # Pick snippet from the field with the highest occurrence count.
            best_field_text: Optional[str] = None
            best_field_score = -1
            for text in fields.values():
                s = _score_occurrences(text, q)
                if s > best_field_score and text:
                    best_field_score = s
                    best_field_text = text

            snippet_source = best_field_text or transcript or ""
            snippet = _best_snippet(snippet_source, q, target_len=200)
            if not snippet:
                snippet = filename

            # Combined score: prioritize semantic score, with
            # keyword_score as a small tie-breaker.
            combined_score = float(semantic_score) if semantic_score > 0.0 else float(keyword_score)

            results.append(
                {
                    "conversation_id": conversation_id,
                    "filename": filename,
                    "snippet": snippet,
                    "score": combined_score,
                }
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        logger.info("Search finished results=%s", len(results))
        return results


_provider: SearchProvider = KeywordSearchProvider()


def set_search_provider(provider: SearchProvider) -> None:
    global _provider
    _provider = provider


def search_conversations(query: str) -> List[SearchResult]:
    return _provider.search(query)
