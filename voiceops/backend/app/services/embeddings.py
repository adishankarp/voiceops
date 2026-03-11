from __future__ import annotations

import logging
import os
from typing import List

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from app.config import MODEL_NAMES
from app.core.errors import ExternalServiceError
from app.core.resilience import retry_call, run_with_timeout

_EMBEDDING_MODEL = MODEL_NAMES["embeddings"]
_EMBEDDING_TIMEOUT_SECONDS = float(os.environ.get("VOICEOPS_EMBEDDING_TIMEOUT_SECONDS", "20"))
_EMBEDDING_RETRY_ATTEMPTS = int(os.environ.get("VOICEOPS_OPENAI_RETRY_ATTEMPTS", "3"))
_client = OpenAI()
logger = logging.getLogger(__name__)


def embed_text(text: str) -> List[float]:
    """
    Compute a vector embedding for the given text using OpenAI.

    Intended for semantic search over conversations.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    logger.info("Embedding request started text_length=%s model=%s", len(cleaned), _EMBEDDING_MODEL)

    def _create_embedding():
        return _client.embeddings.create(
            model=_EMBEDDING_MODEL,
            input=cleaned,
        )

    try:
        resp = retry_call(
            run_with_timeout,
            _create_embedding,
            timeout_seconds=_EMBEDDING_TIMEOUT_SECONDS,
            timeout_message="Embedding request timed out",
            attempts=_EMBEDDING_RETRY_ATTEMPTS,
            retry_exceptions=(APIConnectionError, APITimeoutError, InternalServerError, RateLimitError),
            operation_name="openai_embedding",
        )
    except ExternalServiceError:
        logger.exception("Embedding request timed out")
        raise
    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as exc:
        logger.exception("Embedding request failed after retries")
        raise ExternalServiceError(
            "Embedding request failed",
            code="embedding_failed",
            details={"model": _EMBEDDING_MODEL},
        ) from exc

    logger.info("Embedding request finished vector_size=%s", len(resp.data[0].embedding))
    return list(resp.data[0].embedding)
