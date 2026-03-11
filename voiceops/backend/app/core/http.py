from __future__ import annotations

import logging
import traceback
import uuid
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import AppError


logger = logging.getLogger(__name__)
HTTP_422_STATUS = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)


def _request_id(request: Request) -> str:
    existing = request.scope.get("request_id")
    if isinstance(existing, str) and existing:
        request.state.request_id = existing
        return existing
    value = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.scope["request_id"] = value
    request.state.request_id = value
    return value


def _validation_details(exc: RequestValidationError) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for err in exc.errors():
        details.append(
            {
                "field": ".".join(str(part) for part in err.get("loc", [])),
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "validation_error"),
            }
        )
    return details


def install_exception_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):  # type: ignore[override]
        request_id = _request_id(request)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", _request_id(request))
        logger.warning("Request validation failed request_id=%s errors=%s", request_id, exc.errors())
        return JSONResponse(
            status_code=HTTP_422_STATUS,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": _validation_details(exc),
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", _request_id(request))
        logger.warning("Application error request_id=%s code=%s message=%s", request_id, exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=exc.to_response(request_id=request_id))

    @app.exception_handler(HTTPException)
    async def handle_http_error(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", _request_id(request))
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        payload: Dict[str, Any] = {
            "error": {
                "code": "http_error",
                "message": detail,
                "request_id": request_id,
            }
        }
        if not isinstance(exc.detail, str):
            payload["error"]["details"] = exc.detail
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", _request_id(request))
        logger.exception("Unhandled error request_id=%s", request_id)
        trace = traceback.format_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_server_error",
                    "message": str(exc) or "An unexpected error occurred",
                    "trace": trace,
                    "request_id": request_id,
                }
            },
        )
