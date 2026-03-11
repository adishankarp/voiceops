from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from typing import IO

from app.config import DATA_DIR

_CONVERSATIONS_FILE = DATA_DIR / "conversations.json"


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _CONVERSATIONS_FILE.exists():
        _CONVERSATIONS_FILE.write_text("[]", encoding="utf-8")


def _lock(f: IO[str], exclusive: bool) -> None:
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    except (AttributeError, OSError):
        pass


def _unlock(f: IO[str]) -> None:
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (AttributeError, OSError):
        pass


def _load_all() -> list[dict[str, object]]:
    _ensure_file()
    with open(_CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
        _lock(f, exclusive=False)
        try:
            data = json.load(f)
        finally:
            _unlock(f)
    return data if isinstance(data, list) else []


def save_conversation(record: dict[str, object]) -> None:
    """Persist a conversation record. Adds created_at if missing."""
    data = dict(record)
    if "created_at" not in data or not data["created_at"]:
        data["created_at"] = datetime.now(timezone.utc).isoformat()
    _ensure_file()
    tmp = _CONVERSATIONS_FILE.with_suffix(".tmp")
    with open(_CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
        _lock(f, exclusive=True)
        try:
            raw = json.load(f)
            records = raw if isinstance(raw, list) else []
            by_id = {r["id"]: r for r in records}
            by_id[data["id"]] = data
            with open(tmp, "w", encoding="utf-8") as out:
                json.dump(list(by_id.values()), out, indent=2, ensure_ascii=False)
            os.replace(tmp, _CONVERSATIONS_FILE)
        finally:
            _unlock(f)


def get_conversation(conversation_id: str) -> dict[str, object] | None:
    """Return one conversation by id, or None."""
    records = _load_all()
    for r in records:
        if r.get("id") == conversation_id:
            return r
    return None


def list_conversations() -> list[dict[str, object]]:
    """Return all conversation records (e.g. sorted by created_at descending)."""
    records = _load_all()
    records.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return records


def delete_conversation_by_id(conversation_id: str) -> None:
    """Delete a conversation by id from the JSON store."""
    _ensure_file()
    tmp = _CONVERSATIONS_FILE.with_suffix(".tmp")
    with open(_CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
        _lock(f, exclusive=True)
        try:
            raw = json.load(f)
            records = raw if isinstance(raw, list) else []
            filtered = [c for c in records if c.get("id") != conversation_id]
            with open(tmp, "w", encoding="utf-8") as out:
                json.dump(filtered, out, indent=2, ensure_ascii=False)
            os.replace(tmp, _CONVERSATIONS_FILE)
        finally:
            _unlock(f)
