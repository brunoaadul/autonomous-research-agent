from datetime import datetime

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The research topic to investigate",
    )


class ResearchArea(BaseModel):
    area: str
    description: str


class ResearchResponse(BaseModel):
    conversation_id: str
    agent: str
    version: str
    topic: str
    status: str
    research_type: str
    generated_at: datetime
    executive_summary: str
    keywords: list[str]
    research_questions: list[str]
    research_areas: list[ResearchArea]
    findings: list[str]
    sources: list[str]
    limitations: list[str]
    recommended_next_steps: list[str]
