from __future__ import annotations

import json
import logging
from typing import Optional, TypedDict

from fastapi import APIRouter
from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from pydantic import BaseModel, Field, field_validator

from app.config import MODEL_NAMES, OPENAI_API_KEY
from app.core.errors import AppError, ExternalServiceError
from app.core.resilience import retry_call
from app.services.search import search_conversations
from app.services.storage import get_conversation
from app.services.decision_log import log_decision

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        if len(cleaned) > 4000:
            raise ValueError("question must be at most 4000 characters")
        return cleaned


class ChatSource(TypedDict):
    conversation_id: str
    filename: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


def _get_client() -> OpenAI:
    api_key = OPENAI_API_KEY
    if not api_key:
        raise AppError(code="configuration_error", message="OPENAI_API_KEY environment variable is not set", status_code=500)
    return OpenAI(api_key=api_key)


_model = MODEL_NAMES["chat"]

_SYSTEM_PROMPT = (
    "You are a helpful assistant for sales conversation analysis. "
    "Answer the user's question using ONLY the provided context. "
    "If the context does not contain the answer, say you don't have enough information."
)


def _render_conversation_context(conv: dict[str, object], *, excerpt: str | None = None) -> str:
    conv_id = str(conv.get("id") or "")
    filename = str(conv.get("filename") or "")
    transcript = str(conv.get("transcript") or "")
    insights = conv.get("insights") or {}

    parts: list[str] = [f"CONVERSATION {conv_id}", f"FILENAME: {filename}"]
    if excerpt:
        parts.append("TRANSCRIPT EXCERPT:")
        parts.append(excerpt)
    elif transcript:
        parts.append("TRANSCRIPT:")
        parts.append(transcript[:1200])

    if insights:
        parts.append("INSIGHTS JSON:")
        parts.append(json.dumps(insights, ensure_ascii=False))

    return "\n".join(parts).strip()


def _build_context(conversations: list[dict[str, object]], excerpts_by_id: dict[str, str]) -> str:
    blocks: list[str] = []
    for conv in conversations:
        conv_id = str(conv.get("id") or "")
        blocks.append(_render_conversation_context(conv, excerpt=excerpts_by_id.get(conv_id)))
    return "\n\n---\n\n".join([b for b in blocks if b])


@router.post("")
def chat(req: ChatRequest) -> ChatResponse:
    question = req.question
    logger.info("POST /chat called conversation_id=%s question_length=%s", req.conversation_id, len(question))

    conversations: list[dict[str, object]] = []
    excerpts_by_id: dict[str, str] = {}
    sources: list[ChatSource] = []

    if req.conversation_id:
        conv = get_conversation(req.conversation_id)
        if not conv:
            raise AppError(code="conversation_not_found", message="Conversation not found", status_code=404)
        conversations = [conv]
        sources = [
            {
                "conversation_id": str(conv.get("id") or ""),
                "filename": str(conv.get("filename") or ""),
            }
        ]
    else:
        matches = search_conversations(question)[:3]
        if not matches:
            return ChatResponse(
                answer="I couldn't find any conversations matching your question yet. Try a different keyword or upload/analyze more conversations.",
                sources=[],
            )

        for m in matches:
            conv_id = m.get("conversation_id", "")
            conv = get_conversation(conv_id)
            if not conv:
                continue
            conversations.append(conv)
            excerpts_by_id[str(conv.get("id") or "")] = str(m.get("snippet") or "")
            sources.append(
                {
                    "conversation_id": str(conv.get("id") or ""),
                    "filename": str(conv.get("filename") or ""),
                }
            )

        if not conversations:
            return ChatResponse(
                answer="I found potential matches, but couldn't load the underlying conversations from storage.",
                sources=[],
            )

    unique_sources = {(s["conversation_id"], s["filename"]): s for s in sources}
    sources = list(unique_sources.values())

    context = _build_context(conversations, excerpts_by_id)
    MAX_CONTEXT_CHARS = 12000
    context = context[:MAX_CONTEXT_CHARS]

    user_content = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}\n"

    try:
        resp = retry_call(
            _get_client().chat.completions.create,
            model=_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            attempts=3,
            retry_exceptions=(APIConnectionError, APITimeoutError, InternalServerError, RateLimitError),
            operation_name="openai_chat",
        )
    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as exc:
        logger.exception("Chat completion failed after retries")
        raise ExternalServiceError(
            "Chat completion failed",
            code="chat_failed",
            details={"model": _model},
        ) from exc
    raw = (resp.choices[0].message.content or "").strip()
    logger.debug("Chat raw model output: %s", raw)

    answer = raw or "I couldn't find enough information in the provided conversations."

    # Log the AI decision for observability
    try:
        log_decision(
            stage="chat",
            model=_model,
            input_preview=question,
            output_preview=answer,
            conversation_id=(req.conversation_id if req.conversation_id else None),
        )
    except Exception as e:
        logger.debug("Decision log failed: %s", e)

    logger.info("Chat request finished sources=%s", len(sources))
    return ChatResponse(answer=answer, sources=sources)
