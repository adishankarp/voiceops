from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DATA_DIR, UPLOAD_DIR
from app.core.http import install_exception_handlers
from app.core.logging import configure_logging
from app.routes import conversations, search, chat, patterns
from app.schemas import DebugInfoResponse, StatusResponse

configure_logging()

app = FastAPI(title="VoiceOps API")

# Production: ensure storage directories exist (e.g. /data, /data/uploads on Railway)
@app.on_event("startup")
def _ensure_storage_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_exception_handlers(app)


@app.get("/", response_model=StatusResponse)
def health() -> StatusResponse:
    return StatusResponse(status="VoiceOps backend running")


@app.get("/debug", response_model=DebugInfoResponse)
def debug_info() -> DebugInfoResponse:
    return DebugInfoResponse(
        status="ok",
        routes=[
            "/conversations",
            "/search",
            "/chat",
            "/patterns",
        ],
    )


app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(patterns.router, prefix="/patterns", tags=["patterns"])
