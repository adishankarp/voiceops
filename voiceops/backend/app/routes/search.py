import logging

from fastapi import APIRouter

from app.schemas import SearchResultResponse

from app.services.search import search_conversations

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=list[SearchResultResponse])
def search(query: str = ""):
    logger.info("GET /search called query=%s", query)
    return search_conversations(query)
