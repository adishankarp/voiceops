from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, TypedDict

import whisper

from app.config import MODEL_NAMES
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


def normalize_audio(input_path: str) -> str:
    """
    Normalize arbitrary audio to 16kHz mono WAV using ffmpeg.

    Returns the path to the normalized file (input_path + ".wav").
    """
    output_path = f"{input_path}.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        output_path,
    ]

    logger.info("Normalizing audio with ffmpeg input=%s output=%s", input_path, output_path)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("ffmpeg invocation failed input=%s", input_path)
        raise TranscriptionError(f"Audio normalization failed: {e}") from e

    if proc.returncode != 0:
        logger.error(
            "ffmpeg failed input=%s returncode=%s stderr=%s",
            input_path,
            proc.returncode,
            proc.stderr.strip(),
        )
        raise TranscriptionError(
            f"Audio normalization failed with status {proc.returncode}: {proc.stderr or proc.stdout}"
        )

    logger.info("Audio normalization completed input=%s output=%s", input_path, output_path)
    return output_path


@dataclass(frozen=True)
class WhisperProvider:
    model: Any

    def transcribe(self, file_path: str) -> TranscriptionResult:
        try:
            normalized_path = normalize_audio(file_path)
            result: Dict[str, Any] = self.model.transcribe(normalized_path)
        except Exception as e:  # noqa: BLE001
            raise TranscriptionError(f"Whisper transcription failed: {e}") from e

        text = str(result.get("text") or "").strip()
        raw_segments = result.get("segments") or []

        segments: List[TranscriptionSegment] = []
        if isinstance(raw_segments, list):
            for seg in raw_segments:
                if not isinstance(seg, dict):
                    continue
                start = float(seg.get("start", 0.0))
                end = float(seg.get("end", 0.0))
                seg_text = str(seg.get("text") or "").strip()
                segments.append({"start": start, "end": end, "text": seg_text})

        return {"text": text, "segments": segments}


_MODEL = whisper.load_model(MODEL_NAMES["transcription"])
_PROVIDER: TranscriptionProvider = WhisperProvider(model=_MODEL)
_TRANSCRIPTION_TIMEOUT_SECONDS = float(os.environ.get("VOICEOPS_TRANSCRIPTION_TIMEOUT_SECONDS", "300"))


def set_transcription_provider(provider: TranscriptionProvider) -> None:
    """
    Swap the transcription provider (e.g., for tests or future providers).
    """
    global _PROVIDER
    _PROVIDER = provider


def transcribe_audio(file_path: str) -> TranscriptionResult:
    """
    Transcribe an audio file using the configured provider.
    """
    if not file_path or not isinstance(file_path, str):
        raise TranscriptionError("file_path must be a non-empty string")
    logger.info("Transcription started file_path=%s", file_path)
    try:
        result = run_with_timeout(
            _PROVIDER.transcribe,
            file_path,
            timeout_seconds=_TRANSCRIPTION_TIMEOUT_SECONDS,
            timeout_message="Transcription timed out",
        )
    except ExternalServiceError as exc:
        logger.exception("Transcription timed out file_path=%s", file_path)
        raise TranscriptionError(exc.message) from exc
    logger.info("Transcription finished file_path=%s text_length=%s", file_path, len(result.get("text", "")))
    return result
