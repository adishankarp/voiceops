import logging

from fastapi import APIRouter

from app.schemas import PatternResponse
from app.services.patterns import detect_patterns
from app.services.storage import list_conversations

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=list[PatternResponse])
def get_patterns() -> list[PatternResponse]:
    logger.info("GET /patterns called")
    conversations = list_conversations()
    raw = detect_patterns(conversations)
    return [PatternResponse(label=p["label"], description=p.get("description", "")) for p in raw]
