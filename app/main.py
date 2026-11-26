
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import auth_router, require_current_user
from app.conversations import conversations_router
from app.database import auth_store
from app.database.errors import database_call
from app.schemas.research import ResearchRequest, ResearchResponse
from app.research import run_research


PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

app = FastAPI(
    title="Crokuta Research Agent",
    description="Autonomous research and intelligence API with a multi-provider LLM gateway.",
    version="0.2.0",
)

app.include_router(auth_router)
app.include_router(conversations_router)
app.mount(
    "/static",
    StaticFiles(directory=PUBLIC_DIR / "static"),
    name="static",
)


@app.get("/", tags=["System"])
def root(request: Request):
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse(PUBLIC_DIR / "index.html")
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


@app.get("/app", include_in_schema=False)
def web_app():
    return FileResponse(PUBLIC_DIR / "index.html")


@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy"}


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


@app.post("/research", tags=["Research"], response_model=ResearchResponse)
def research_endpoint(
    request: ResearchRequest,
    current_user: dict = Depends(require_current_user),
):
    try:
        report = run_research(request.topic)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
    return database_call(
        auth_store.create_conversation,
        current_user["id"],
        report,
    )
