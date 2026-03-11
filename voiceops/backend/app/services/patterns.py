from __future__ import annotations

import json
import logging
from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from app.config import MODEL_NAMES, OPENAI_API_KEY
from app.core.resilience import retry_call

logger = logging.getLogger(__name__)

PATTERNS_SYSTEM = """You are a sales conversation analyst. You will receive summaries and insight snippets from multiple sales conversations.
Identify the top 5 recurring patterns or themes across these conversations. Examples: common objections, repeated pain points, recurring closing language, thematic trends, or behavioral patterns.
Output valid JSON only, no markdown or explanation. Use this exact structure:
{"patterns": [{"label": "short title", "description": "one sentence explaining the pattern"}, ...]}
- label: short title (e.g. "Price objections")
- description: one clear sentence describing the pattern
Return at most 5 patterns. If there are fewer than 5 clear patterns, return fewer. If there is no meaningful data, return {"patterns": []}."""


def _build_conversation_context(conv: dict[str, Any]) -> str:
    parts = []
    summary = conv.get("summary")
    if summary and isinstance(summary, str) and summary.strip():
        parts.append(f"Summary: {summary.strip()}")
    insights = conv.get("insights")
    if isinstance(insights, dict):
        for key in ("pain_points", "objections", "buying_signals", "closing_attempts", "key_moments"):
            items = insights.get(key)
            if not isinstance(items, list):
                continue
            texts = []
            for item in items:
                if isinstance(item, dict) and item.get("text"):
                    texts.append(str(item["text"]).strip())
                elif isinstance(item, dict) and item.get("summary"):
                    texts.append(str(item["summary"]).strip())
            if texts:
                parts.append(f"{key}: " + "; ".join(texts[:5]))
    return "\n".join(parts) if parts else ""


def _build_user_message(conversations: list[dict[str, Any]]) -> str:
    MAX_TOTAL_CHARS = 18000
    blocks = []
    total = 0
    for i, conv in enumerate(conversations):
        block = _build_conversation_context(conv)
        if not block:
            continue
        prefixed = f"--- Conversation {i + 1} ---\n{block}"
        if total + len(prefixed) > MAX_TOTAL_CHARS:
            prefixed = prefixed[: MAX_TOTAL_CHARS - total]
            blocks.append(prefixed)
            break
        blocks.append(prefixed)
        total += len(prefixed)
    return "\n\n".join(blocks) if blocks else ""


def detect_patterns(conversations: list[dict[str, Any]]) -> list[dict[str, str]]:
    """
    Detect up to 5 recurring patterns across the given conversations using the LLM.
    Returns a list of {"label": str, "description": str}. Returns [] on no data or on error.
    """
    if not conversations:
        return []

    payload = _build_user_message(conversations)
    if not payload.strip():
        logger.info("Pattern detection skipped: no summary or insight data in conversations")
        return []

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        model = MODEL_NAMES.get("insights", "gpt-4o-mini")

        def _complete() -> Any:
            return client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PATTERNS_SYSTEM},
                    {"role": "user", "content": f"Analyze these conversations and return the JSON object with patterns.\n\n{payload}"},
                ],
                temperature=0.2,
            )

        response = retry_call(
            _complete,
            attempts=3,
            retry_exceptions=(APIConnectionError, APITimeoutError, InternalServerError, RateLimitError),
            operation_name="openai_patterns",
        )
        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)
        data = json.loads(raw)
        patterns = data.get("patterns")
        if not isinstance(patterns, list):
            return []
        result = []
        for p in patterns[:5]:
            if not isinstance(p, dict):
                continue
            label = p.get("label")
            description = p.get("description", "")
            if label is None:
                continue
            result.append({"label": str(label).strip(), "description": str(description).strip()})
        logger.info("Pattern detection finished count=%s", len(result))
        return result
    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
        logger.warning("Pattern detection failed (LLM error): %s", e)
        return []
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.warning("Pattern detection failed (parse error): %s", e)
        return []
