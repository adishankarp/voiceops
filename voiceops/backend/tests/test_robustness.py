from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

from app.core.background import run_guarded_background_task
from app.core.errors import AppError
from app.core.http import install_exception_handlers


class EchoRequest(BaseModel):
    question: str = Field(..., min_length=1)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        return cleaned


class RobustnessTests(unittest.TestCase):
    def test_validation_errors_use_structured_response(self) -> None:
        app = FastAPI()
        install_exception_handlers(app)

        @app.post("/echo")
        def echo(payload: EchoRequest) -> dict:
            return payload.model_dump()

        client = TestClient(app)
        response = client.post("/echo", json={"question": "   "})

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertEqual(body["error"]["code"], "validation_error")
        self.assertEqual(body["error"]["message"], "Request validation failed")
        self.assertEqual(body["error"]["details"][0]["field"], "body.question")
        self.assertIn("request_id", body["error"])
        self.assertEqual(response.headers["x-request-id"], body["error"]["request_id"])

    def test_app_errors_use_structured_response(self) -> None:
        app = FastAPI()
        install_exception_handlers(app)

        @app.get("/boom")
        def boom() -> None:
            raise AppError(code="sample_error", message="sample message", status_code=409)

        client = TestClient(app)
        response = client.get("/boom")

        self.assertEqual(response.status_code, 409)
        body = response.json()
        self.assertEqual(body["error"]["code"], "sample_error")
        self.assertEqual(body["error"]["message"], "sample message")
        self.assertIn("request_id", body["error"])

    def test_guarded_background_task_swallows_exceptions(self) -> None:
        def explode() -> None:
            raise RuntimeError("background failure")

        run_guarded_background_task("explode", explode)


if __name__ == "__main__":
    unittest.main()
