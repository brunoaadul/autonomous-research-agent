
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.llm.gateway import llm_gateway
from app.schemas.llm import LLMRequest
from app.research import run_research


app = FastAPI(
    title="Crokuta Research Agent",
    description="Autonomous research and intelligence API with a multi-provider LLM gateway.",
    version="0.2.0",
)


class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The research topic to investigate",
    )


@app.get("/", tags=["System"])
def root():
    return {
        "name": "Crokuta Research Agent",
        "version": "0.2.0",
        "status": "running",
        "capabilities": [
            "research",
            "multi-provider-llm",
            "local-model-inference",
        ],
    }


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}


@app.post("/api/v1/llm/chat", tags=["LLM"])
def chat_endpoint(request: LLMRequest):
    try:
        return llm_gateway.generate(request)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        )


@app.get("/api/v1/llm/providers", tags=["LLM"])
def list_providers():
    return {
        "providers": [
            {"name": "openai", "type": "cloud"},
            {"name": "anthropic", "type": "cloud"},
            {"name": "gemini", "type": "cloud"},
            {"name": "groq", "type": "cloud"},
            {"name": "openrouter", "type": "cloud"},
            {"name": "ollama", "type": "local"},
            {"name": "lm_studio", "type": "local"},
            {"name": "vllm", "type": "self-hosted"},
            {"name": "custom", "type": "compatible"},
        ]
    }


@app.post("/research", tags=["Research"])
def research_endpoint(request: ResearchRequest):
    try:
        return run_research(request.topic)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
