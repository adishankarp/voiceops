from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, TypedDict

from openai import OpenAI

from app.config import OPENAI_API_KEY
from app.core.errors import ExternalServiceError
from app.core.resilience import run_with_timeout

logger = logging.getLogger(__name__)


class TranscriptionSegment(TypedDict):
    start: float
    end: float
    text: str


class TranscriptionResult(TypedDict):
    text: str
    segments: List[TranscriptionSegment]


class TranscriptionError(RuntimeError):
    pass


class TranscriptionProvider(Protocol):
    def transcribe(self, file_path: str) -> TranscriptionResult: ...


# OpenAI Whisper API model (API uses "whisper-1"; local model names like "base" are not used)
WHISPER_API_MODEL = "whisper-1"


@dataclass(frozen=True)
class OpenAIWhisperProvider:
    """Transcription via OpenAI Whisper API (no local Whisper/Torch)."""

    client: OpenAI

    def transcribe(self, file_path: str) -> TranscriptionResult:
        path = Path(file_path)
        if not path.is_file():
            raise TranscriptionError(f"Audio file not found: {file_path}")

        try:
            with open(path, "rb") as f:
                response = self.client.audio.transcriptions.create(
                    model=WHISPER_API_MODEL,
                    file=f,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )
        except Exception as e:  # noqa: BLE001
            logger.exception("OpenAI Whisper API failed file_path=%s", file_path)
            raise TranscriptionError(f"Transcription failed: {e}") from e

        text = (getattr(response, "text", None) or "").strip()
        segments: List[TranscriptionSegment] = []

        raw_segments = getattr(response, "segments", None) or []
        if isinstance(raw_segments, list):
            for seg in raw_segments:
                if isinstance(seg, dict):
                    start = float(seg.get("start", 0.0))
                    end = float(seg.get("end", 0.0))
                    seg_text = str(seg.get("text") or "").strip()
                else:
                    if not hasattr(seg, "start") or not hasattr(seg, "end"):
                        continue
                    start = float(getattr(seg, "start", 0.0))
                    end = float(getattr(seg, "end", 0.0))
                    seg_text = (getattr(seg, "text", None) or "").strip()
                segments.append({"start": start, "end": end, "text": seg_text})

        return {"text": text, "segments": segments}


def _client() -> OpenAI:
    if not (OPENAI_API_KEY and OPENAI_API_KEY.strip()):
        raise TranscriptionError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=OPENAI_API_KEY)


_PROVIDER: Optional[TranscriptionProvider] = None
_TRANSCRIPTION_TIMEOUT_SECONDS = float(os.environ.get("VOICEOPS_TRANSCRIPTION_TIMEOUT_SECONDS", "300"))


def _get_provider() -> TranscriptionProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = OpenAIWhisperProvider(client=_client())
    return _PROVIDER


def set_transcription_provider(provider: TranscriptionProvider) -> None:
    """
    Swap the transcription provider (e.g., for tests or future providers).
    """
    global _PROVIDER
    _PROVIDER = provider


def transcribe_audio(file_path: str) -> TranscriptionResult:
    """
    Transcribe an audio file using the OpenAI Whisper API.
    """
    if not file_path or not isinstance(file_path, str):
        raise TranscriptionError("file_path must be a non-empty string")
    logger.info("Transcription started file_path=%s", file_path)
    try:
        result = run_with_timeout(
            _get_provider().transcribe,
            file_path,
            timeout_seconds=_TRANSCRIPTION_TIMEOUT_SECONDS,
            timeout_message="Transcription timed out",
        )
    except ExternalServiceError as exc:
        logger.exception("Transcription timed out file_path=%s", file_path)
        raise TranscriptionError(exc.message) from exc
    logger.info("Transcription finished file_path=%s text_length=%s", file_path, len(result.get("text", "")))
    return result
