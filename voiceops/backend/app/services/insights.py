from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Protocol

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, ValidationError

from app.config import MODEL_NAMES, OPENAI_API_KEY
from app.core.errors import ExternalServiceError
from app.core.resilience import retry_call

logger = logging.getLogger(__name__)
_OPENAI_RETRY_ATTEMPTS = int(os.environ.get("VOICEOPS_OPENAI_RETRY_ATTEMPTS", "3"))


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------


class KeyMoment(BaseModel):
    timestamp: float = Field(..., description="Time in seconds")
    summary: str = Field(..., description="Brief summary of the moment")


class InsightItem(BaseModel):
    text: str = Field(..., description="Insight text")
    timestamp: Optional[float] = Field(
        default=None,
        description="Time in seconds from conversation start, or null if unknown",
    )


class Insights(BaseModel):
    pain_points: List[InsightItem] = Field(default_factory=list, description="Customer pain points mentioned")
    objections: List[InsightItem] = Field(default_factory=list, description="Objections raised")
    buying_signals: List[InsightItem] = Field(default_factory=list, description="Signals of purchase intent")
    closing_attempts: List[InsightItem] = Field(default_factory=list, description="Rep's closing attempts")
    key_moments: List[KeyMoment] = Field(default_factory=list, description="Notable moments with timestamp")
    sentiment_score: float = Field(..., ge=0.0, le=1.0, description="Overall sentiment 0-1")


# ---------------------------------------------------------------------------
# Provider protocol (for swapping LLM later)
# ---------------------------------------------------------------------------


class InsightsProvider(Protocol):
    def extract(self, transcript: str) -> Insights: ...


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM = """You are a sales conversation analyst. Extract structured insights from the transcript.
Output valid JSON only, no markdown or explanation. Use this exact structure:
{
  "pain_points": [{"text": "string", "timestamp": number | null}],
  "objections": [{"text": "string", "timestamp": number | null}],
  "buying_signals": [{"text": "string", "timestamp": number | null}],
  "closing_attempts": [{"text": "string", "timestamp": number | null}],
  "key_moments": [{"timestamp": number, "summary": "string"}],
  "sentiment_score": number
}
- pain_points: customer problems or frustrations
- objections: resistance or concerns
- buying_signals: signs of interest or intent to buy
- closing_attempts: rep's attempts to close or next steps
- key_moments: important moments with timestamp in seconds and short summary
- sentiment_score: overall conversation sentiment from 0.0 (negative) to 1.0 (positive)

When possible, set timestamps based on the transcript timestamps (seconds from conversation start).
If you cannot determine a timestamp for an item, use null for its timestamp.
"""


def _build_user_message(transcript: str) -> str:
    return f"Analyze this sales conversation transcript and return the JSON object only.\n\nTranscript:\n{transcript}"


SUMMARY_SYSTEM = """You are a sales conversation analyst. Summarize the conversation in one short paragraph (2-4 sentences).
Include: what was discussed, key outcomes or next steps, and the main takeaway.
Output plain text only. Do not use JSON, markdown, or bullet points."""


def generate_summary(transcript: str) -> str:
    """
    Generate a short paragraph summary of a sales conversation transcript.
    Uses the same OpenAI model and resilience pattern as insights extraction.
    """
    if not transcript or not transcript.strip():
        return ""

    MAX_CHARS = 15000
    transcript = transcript[:MAX_CHARS]

    provider = get_insights_provider()
    if not isinstance(provider, OpenAIInsightsProvider):
        # Fallback for non-OpenAI providers: no summary
        logger.warning("generate_summary called with non-OpenAI provider; returning empty summary")
        return ""

    user_message = f"Summarize this sales conversation in one short paragraph (2-4 sentences).\n\nTranscript:\n{transcript}"
    logger.info("Summary generation started transcript_length=%s model=%s", len(transcript), provider.model)

    def _complete(system_prompt: str, temperature: float):
        return provider.client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )

    try:
        response = retry_call(
            _complete,
            SUMMARY_SYSTEM,
            0.2,
            attempts=_OPENAI_RETRY_ATTEMPTS,
            retry_exceptions=(APIConnectionError, APITimeoutError, InternalServerError, RateLimitError),
            operation_name="openai_summary",
        )
    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as exc:
        logger.exception("Summary generation failed after retries")
        raise ExternalServiceError(
            "Summary generation failed",
            code="summary_failed",
            details={"model": provider.model},
        ) from exc

    raw = (response.choices[0].message.content or "").strip()
    logger.info("Summary generation finished model=%s", provider.model)
    return raw


def _parse_insights(raw: str) -> Insights:
    """Parse and validate raw string as Insights. Raises ValueError on failure."""
    # Strip markdown code blocks if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    data: Dict[str, Any] = json.loads(text)

    # Backwards compatibility: allow string lists as well as object lists
    # for the four structured insight arrays. Normalize into
    # [{"text": str, "timestamp": float|None}, ...] before validation.
    for field in ("pain_points", "objections", "buying_signals", "closing_attempts"):
        value = data.get(field)
        if value is None:
            continue
        if not isinstance(value, list):
            continue
        normalized: List[Dict[str, Any]] = []
        for item in value:
            if isinstance(item, str):
                normalized.append({"text": item, "timestamp": None})
            elif isinstance(item, dict):
                text_val = str(item.get("text") or "").strip()
                ts_raw = item.get("timestamp", None)
                ts: Optional[float]
                if ts_raw is None:
                    ts = None
                else:
                    try:
                        ts = float(ts_raw)
                    except (TypeError, ValueError):
                        ts = None
                normalized.append({"text": text_val, "timestamp": ts})
        data[field] = normalized

    insights = Insights.model_validate(data)
    clamped = max(0.0, min(1.0, insights.sentiment_score))
    return insights.model_copy(update={"sentiment_score": clamped})


class OpenAIInsightsProvider:
    """Extract insights using OpenAI chat completion."""

    def __init__(self, api_key: Optional[str] = None, model: str = MODEL_NAMES["insights"]):
        self.client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        self.model = model

    def extract(self, transcript: str) -> Insights:
        if not transcript or not transcript.strip():
            return Insights(
                pain_points=[],
                objections=[],
                buying_signals=[],
                closing_attempts=[],
                key_moments=[],
                sentiment_score=0.5,
            )

        MAX_CHARS = 15000
        transcript = transcript[:MAX_CHARS]

        user_message = _build_user_message(transcript)
        logger.info("Insights extraction started transcript_length=%s model=%s", len(transcript), self.model)

        def _complete(system_prompt: str, temperature: float):
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
            )

        try:
            response = retry_call(
                _complete,
                EXTRACTION_SYSTEM,
                0.2,
                attempts=_OPENAI_RETRY_ATTEMPTS,
                retry_exceptions=(APIConnectionError, APITimeoutError, InternalServerError, RateLimitError),
                operation_name="openai_insights",
            )
        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as exc:
            logger.exception("Insights extraction failed after retries")
            raise ExternalServiceError(
                "Insights extraction failed",
                code="insights_failed",
                details={"model": self.model},
            ) from exc
        raw = (response.choices[0].message.content or "").strip()
        logger.debug("Insights raw model output: %s", raw)

        try:
            insights = _parse_insights(raw)
            logger.info("Insights extraction finished model=%s", self.model)
            return insights
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.warning("Insights parse failed (retry once): %s", e)
            try:
                response = retry_call(
                    _complete,
                    EXTRACTION_SYSTEM + "\nRemember: output only valid JSON.",
                    0.1,
                    attempts=_OPENAI_RETRY_ATTEMPTS,
                    retry_exceptions=(APIConnectionError, APITimeoutError, InternalServerError, RateLimitError),
                    operation_name="openai_insights_parse_retry",
                )
            except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as exc:
                logger.exception("Insights extraction retry failed after retries")
                raise ExternalServiceError(
                    "Insights extraction failed",
                    code="insights_failed",
                    details={"model": self.model},
                ) from exc
            raw_retry = (response.choices[0].message.content or "").strip()
            logger.debug("Insights retry raw output: %s", raw_retry)
            insights = _parse_insights(raw_retry)
            logger.info("Insights extraction finished after parse retry model=%s", self.model)
            return insights


_default_provider: Optional[InsightsProvider] = None


def set_insights_provider(provider: InsightsProvider) -> None:
    """Set the insights provider (e.g. for tests or another LLM)."""
    global _default_provider
    _default_provider = provider


def get_insights_provider() -> InsightsProvider:
    """Return the configured provider, or a default OpenAI one."""
    global _default_provider
    if _default_provider is not None:
        return _default_provider
    _default_provider = OpenAIInsightsProvider()
    return _default_provider


def extract_insights(transcript: str) -> Insights:
    """
    Convert a conversation transcript into structured sales insights.
    Uses the configured LLM provider (default: OpenAI).
    """
    return get_insights_provider().extract(transcript)


def build_timeline(insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize insights into a sorted list of timeline events.

    Each event:
      {
        "type": str,
        "timestamp": float,
        "label": str,
      }
    """
    events: List[Dict[str, Any]] = []

    def add_items(type_name: str, items: Optional[List[Any]]) -> None:
        if not items:
            return
        for item in items:
            if not isinstance(item, dict):
                # Support legacy string-only entries by skipping
                # (no timestamp information available).
                continue
            ts_raw = item.get("timestamp")
            if ts_raw is None:
                continue
            try:
                ts = float(ts_raw)
            except (TypeError, ValueError):
                continue
            label = item.get("text") or item.get("summary") or ""
            if not label:
                continue
            events.append(
                {
                    "type": type_name,
                    "timestamp": ts,
                    "label": str(label),
                }
            )

    add_items("pain_point", insights.get("pain_points"))
    add_items("objection", insights.get("objections"))
    add_items("buying_signal", insights.get("buying_signals"))
    add_items("closing_attempt", insights.get("closing_attempts"))

    for km in insights.get("key_moments") or []:
        if not isinstance(km, dict):
            continue
        ts_raw = km.get("timestamp")
        if ts_raw is None:
            continue
        try:
            ts = float(ts_raw)
        except (TypeError, ValueError):
            continue
        summary = km.get("summary") or ""
        if not summary:
            continue
        events.append(
            {
                "type": "key_moment",
                "timestamp": ts,
                "label": str(summary),
            }
        )

    events.sort(key=lambda e: e["timestamp"])
    return events
