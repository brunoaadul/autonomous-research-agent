from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.research import ResearchResponse


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    report: ResearchResponse
    messages: list[ConversationMessage]
    created_at: datetime
    updated_at: datetime


class ConversationMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    provider: str = Field(default="ollama", min_length=1, max_length=100)
    model: str = Field(default="llama3.1", min_length=1, max_length=200)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=1000, ge=1)
    timeout: float = Field(default=120.0, gt=0, le=600)


class ConversationDeleteResponse(BaseModel):
    ok: bool
