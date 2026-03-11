from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 500
    details: Optional[Dict[str, Any]] = field(default=None)

    def to_response(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        if request_id:
            payload["error"]["request_id"] = request_id
        return payload


class ExternalServiceError(AppError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "external_service_error",
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(code=code, message=message, status_code=status_code, details=details)


class PipelineStageError(AppError):
    def __init__(self, stage: str, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            code="pipeline_stage_failed",
            message=message,
            status_code=500,
            details={"stage": stage, **(details or {})},
        )
