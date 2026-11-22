
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.research import run_research


# -------------------------
# Application Configuration
# -------------------------

app = FastAPI(
    title="Crokuta Research Agent",
    description="Autonomous research and intelligence API",
    version="0.1.0",
)


# -------------------------
# Request Models
# -------------------------

class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The topic to investigate",
    )


# -------------------------
# System Endpoints
# -------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "name": "Crokuta Research Agent",
        "status": "running",
    }


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
    }


# -------------------------
# Research Endpoint
# -------------------------

@app.post("/research", tags=["Research"])
def research_endpoint(request: ResearchRequest):
    try:
        return run_research(request.topic)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )
