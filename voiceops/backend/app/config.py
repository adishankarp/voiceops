from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv


load_dotenv()

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_MODEL_NAMES: Dict[str, str] = {
    "transcription": "whisper-1",
    "insights": "gpt-4o-mini",
    "chat": "gpt-4o-mini",
    "embeddings": "text-embedding-3-small",
}


def _parse_model_names(raw: str | None) -> Dict[str, str]:
    if not raw:
        return dict(_DEFAULT_MODEL_NAMES)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("MODEL_NAMES must be a valid JSON object") from exc

    if not isinstance(parsed, dict):
        raise ValueError("MODEL_NAMES must be a JSON object")

    model_names = dict(_DEFAULT_MODEL_NAMES)
    for key, value in parsed.items():
        if key in model_names and isinstance(value, str) and value.strip():
            model_names[key] = value.strip()
    return model_names


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
MODEL_NAMES = _parse_model_names(os.environ.get("MODEL_NAMES"))
# Production defaults: /data, /data/uploads when env not set (e.g. Railway)
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR") or "/data/uploads")
DATA_DIR = Path(os.environ.get("DATA_DIR") or "/data")
