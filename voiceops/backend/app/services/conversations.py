from __future__ import annotations

import shutil
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile, status

from app.config import UPLOAD_DIR
from app.core.errors import AppError


ALLOWED_EXTENSIONS = {".wav", ".mp3"}


def save_audio_upload(file: UploadFile, conversation_id: str) -> Tuple[str, Path]:
    original_name = Path(file.filename or "").name
    if not original_name:
        raise AppError(code="invalid_upload", message="Uploaded file must have a filename", status_code=status.HTTP_400_BAD_REQUEST)
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            code="unsupported_file_type",
            message="Only .wav or .mp3 files are supported",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"allowed_extensions": sorted(ALLOWED_EXTENSIONS)},
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stored_name = f"{conversation_id}_{original_name}"
    dst = UPLOAD_DIR / stored_name
    with dst.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    return original_name, dst
