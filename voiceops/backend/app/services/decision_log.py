from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.storage import get_conversation, save_conversation


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(text: str, limit: int = 200) -> str:
    if text is None:
        return ""
    s = str(text)
    return s[:limit]


def log_decision(
    stage: str,
    model: str,
    input_preview: str,
    output_preview: str,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record an AI decision at a given pipeline stage.

    - stage: e.g. 'transcription', 'insights', 'chat'
    - model: e.g. 'whisper-base', 'gpt-4o-mini'
    - input_preview / output_preview: arbitrary strings, trimmed to 200 chars
    - conversation_id: if provided, append to that conversation's decision_log
    """
    record: Dict[str, Any] = {
        "stage": stage,
        "model": model,
        "timestamp": _now_utc_iso(),
        "input_preview": _preview(input_preview),
        "output_preview": _preview(output_preview),
    }

    if conversation_id:
        conv = get_conversation(conversation_id)
        if not conv:
            conv = {
                "id": conversation_id,
                "filename": "",
                "transcript": "",
                "segments": [],
                "insights": {},
                "created_at": None,
            }

        log = conv.get("decision_log") or []
        if not isinstance(log, list):
            log = []
        log.append(record)
        conv["decision_log"] = log
        save_conversation(conv)

    return record

