
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    provider: str = Field(
        default="ollama",
        description="LLM provider, e.g. openai, anthropic, ollama, groq"
    )

    model: str = Field(
        default="llama3.1",
        description="Provider-specific model identifier"
    )

    messages: list[Message] = Field(
        ...,
        min_length=1,
        description="Conversation messages"
    )

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0
    )

    max_tokens: Optional[int] = Field(
        default=1000,
    )

    api_base: Optional[str] = Field(
        default=None,
        description="Optional custom API endpoint for local or compatible providers"
    )

    api_key: Optional[str] = Field(
        default=None,
        description="Optional request-level API key override"
    )

    timeout: float = Field(
        default=120.0,
        gt=0,
        le=600
    )


class LLMResponse(BaseModel):
    provider: str
    model: str
    content: str
    finish_reason: Optional[str] = None

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    latency_seconds: float

    request_id: Optional[str] = None
