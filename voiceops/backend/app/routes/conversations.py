from uuid import uuid4

import json
import logging

from fastapi import APIRouter, BackgroundTasks, File, UploadFile, status

from app.config import MODEL_NAMES
from app.core.background import run_guarded_background_task
from app.core.errors import AppError
from app.schemas import ConversationResponse, DeleteConversationResponse, UploadConversationResponse
from app.services.conversations import save_audio_upload
from app.services.decision_log import log_decision
from app.services.embeddings import embed_text
from app.services.insights import build_timeline, extract_insights, generate_summary
from app.services.storage import delete_conversation_by_id, get_conversation, list_conversations, save_conversation
from app.services.transcription import transcribe_audio

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_conversation_record(conversation_id: str, filename: str = "") -> dict[str, object]:
    return {
        "id": conversation_id,
        "filename": filename,
        "status": "uploaded",
        "transcript": "",
        "segments": [],
        "insights": {},
        "summary": None,
        "created_at": None,
        "error": None,
    }


@router.post("/upload", response_model=UploadConversationResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_conversation_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    logger.info("POST /conversations/upload called filename=%s content_type=%s", file.filename, file.content_type)
    logger.info("Conversation upload received filename=%s content_type=%s", file.filename, file.content_type)
    conversation_id = str(uuid4())
    original_filename, path = save_audio_upload(file, conversation_id)

    conversation = _build_conversation_record(conversation_id, original_filename)
    save_conversation(conversation)

    background_tasks.add_task(
        run_guarded_background_task,
        "process_conversation",
        process_conversation,
        conversation_id,
        str(path),
    )

    return {"conversation_id": conversation_id, "status": "uploaded"}


def process_conversation(conversation_id: str, file_path: str) -> None:
    logger.info("Pipeline started conversation_id=%s file_path=%s", conversation_id, file_path)
    conversation = get_conversation(conversation_id) or _build_conversation_record(conversation_id)
    conversation["error"] = None

    # 1) Transcribing
    conversation["status"] = "transcribing"
    save_conversation(conversation)
    logger.info("Pipeline stage started conversation_id=%s stage=transcription", conversation_id)

    try:
        transcription = transcribe_audio(file_path)
        conversation["transcript"] = transcription.get("text", "") or ""
        conversation["segments"] = transcription.get("segments", []) or []
        log_decision(
            stage="transcription",
            model=MODEL_NAMES["transcription"],
            input_preview=file_path,
            output_preview=conversation["transcript"],
            conversation_id=conversation_id,
        )
        logger.info("Pipeline stage finished conversation_id=%s stage=transcription", conversation_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline stage failed conversation_id=%s stage=transcription", conversation_id)
        log_decision(
            stage="transcription",
            model=MODEL_NAMES["transcription"],
            input_preview=file_path,
            output_preview=f"ERROR: {e}",
            conversation_id=conversation_id,
        )
        conversation["status"] = "failed"
        conversation["error"] = {"stage": "transcription", "message": str(e)}
        save_conversation(conversation)
        return

    # 2) Extracting insights
    conversation["status"] = "extracting"
    save_conversation(conversation)
    logger.info("Pipeline stage started conversation_id=%s stage=insights", conversation_id)

    try:
        insights = extract_insights(conversation["transcript"])
        insights_dict = insights.model_dump()
        conversation["insights"] = insights_dict
        log_decision(
            stage="insights",
            model=MODEL_NAMES["insights"],
            input_preview=conversation["transcript"],
            output_preview=json.dumps(insights_dict, ensure_ascii=False),
            conversation_id=conversation_id,
        )
        logger.info("Pipeline stage finished conversation_id=%s stage=insights", conversation_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline stage failed conversation_id=%s stage=insights", conversation_id)
        log_decision(
            stage="insights",
            model=MODEL_NAMES["insights"],
            input_preview=conversation["transcript"],
            output_preview=f"ERROR: {e}",
            conversation_id=conversation_id,
        )
        conversation["status"] = "failed"
        conversation["error"] = {"stage": "insights", "message": str(e)}
        save_conversation(conversation)
        return

    # 3) Summary
    logger.info("Pipeline stage started conversation_id=%s stage=summary", conversation_id)
    try:
        summary = generate_summary(conversation["transcript"])
        conversation["summary"] = summary
        log_decision(
            stage="summary",
            model=MODEL_NAMES["insights"],
            input_preview=conversation["transcript"],
            output_preview=summary,
            conversation_id=conversation_id,
        )
        logger.info("Pipeline stage finished conversation_id=%s stage=summary", conversation_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline stage failed conversation_id=%s stage=summary", conversation_id)
        log_decision(
            stage="summary",
            model=MODEL_NAMES["insights"],
            input_preview=conversation["transcript"],
            output_preview=f"ERROR: {e}",
            conversation_id=conversation_id,
        )
        conversation["status"] = "failed"
        conversation["error"] = {"stage": "summary", "message": str(e)}
        save_conversation(conversation)
        return

    # 4) Embeddings (semantic search)
    logger.info("Pipeline stage started conversation_id=%s stage=embedding", conversation_id)
    try:
        # Keep it simple: embed the transcript; truncate to avoid huge payloads.
        text_to_embed = (conversation.get("transcript") or "")[:4000]
        embedding = embed_text(text_to_embed)
        conversation["embedding"] = embedding
        log_decision(
            stage="embedding",
            model=MODEL_NAMES["embeddings"],
            input_preview=text_to_embed,
            output_preview=f"embedding_dims={len(embedding)}",
            conversation_id=conversation_id,
        )
        logger.info("Pipeline stage finished conversation_id=%s stage=embedding", conversation_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("Pipeline stage failed conversation_id=%s stage=embedding", conversation_id)
        log_decision(
            stage="embedding",
            model=MODEL_NAMES["embeddings"],
            input_preview=(conversation.get("transcript") or "")[:200],
            output_preview=f"ERROR: {e}",
            conversation_id=conversation_id,
        )

    # 5) Completed
    conversation["status"] = "complete"
    save_conversation(conversation)
    logger.info("Pipeline finished conversation_id=%s status=complete", conversation_id)


@router.get("", response_model=list[ConversationResponse])
def list_all_conversations():
    logger.info("GET /conversations called")
    convs = list_conversations()

    for c in convs:
        if "status" not in c:
            c["status"] = "complete"

    return convs


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation_detail(conversation_id: str):
    logger.info("GET /conversations/%s called", conversation_id)
    conv = get_conversation(conversation_id)
    if not conv:
        raise AppError(code="conversation_not_found", message="Conversation not found", status_code=status.HTTP_404_NOT_FOUND)
    insights = conv.get("insights") or {}
    if isinstance(insights, dict):
        conv["timeline"] = build_timeline(insights)
    else:
        conv["timeline"] = []
    return conv


@router.delete("/{conversation_id}", response_model=DeleteConversationResponse)
def delete_conversation(conversation_id: str) -> DeleteConversationResponse:
    logger.info("DELETE /conversations/%s called", conversation_id)
    delete_conversation_by_id(conversation_id)
    return DeleteConversationResponse(status="deleted")
