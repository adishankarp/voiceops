from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProcessingStatus = Literal["uploaded", "transcribing", "extracting", "complete", "failed"]


class UploadConversationResponse(BaseModel):
    conversation_id: str
    status: ProcessingStatus


class StatusResponse(BaseModel):
    status: str


class DebugInfoResponse(BaseModel):
    status: str
    routes: list[str]


class ConversationSegmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    start: float = 0
    end: float = 0
    speaker: str | None = None
    timestamp: str | None = None
    text: str = ""


class InsightItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    timestamp: float | None = None


class KeyMomentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: float
    summary: str


class ConversationInsightsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pain_points: list[InsightItemResponse] = Field(default_factory=list)
    objections: list[InsightItemResponse] = Field(default_factory=list)
    buying_signals: list[InsightItemResponse] = Field(default_factory=list)
    closing_attempts: list[InsightItemResponse] = Field(default_factory=list)
    key_moments: list[KeyMomentResponse] = Field(default_factory=list)
    sentiment_score: float | None = None


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    timestamp: float
    label: str


class ConversationErrorResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stage: str
    message: str


class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    filename: str
    status: ProcessingStatus
    title: str | None = None
    date: str | None = None
    duration: str | None = None
    participants: list[str] = Field(default_factory=list)
    transcript: str = ""
    segments: list[ConversationSegmentResponse] = Field(default_factory=list)
    insights: ConversationInsightsResponse = Field(default_factory=ConversationInsightsResponse)
    summary: str | None = None
    timeline: list[TimelineEventResponse] = Field(default_factory=list)
    created_at: str | None = None
    error: ConversationErrorResponse | None = None
    embedding: list[float] | None = None


class DeleteConversationResponse(BaseModel):
    status: Literal["deleted"]


class SearchResultResponse(BaseModel):
    conversation_id: str
    filename: str
    snippet: str
    score: float


class PatternResponse(BaseModel):
    label: str
    description: str = ""
