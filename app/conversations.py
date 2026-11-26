from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_current_user
from app.database import auth_store
from app.database.errors import database_call
from app.llm.gateway import llm_gateway
from app.schemas.conversations import (
    ConversationDeleteResponse,
    ConversationDetail,
    ConversationMessageRequest,
    ConversationSummary,
)
from app.schemas.llm import LLMRequest, LLMResponse, Message


conversations_router = APIRouter(
    prefix="/api/v1/conversations",
    tags=["Conversations"],
)


@conversations_router.get("", response_model=list[ConversationSummary])
def list_conversations(
    current_user: dict = Depends(require_current_user),
):
    return database_call(auth_store.list_conversations, current_user["id"])


@conversations_router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_current_user),
):
    conversation = database_call(
        auth_store.get_conversation,
        current_user["id"],
        conversation_id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@conversations_router.delete(
    "/{conversation_id}",
    response_model=ConversationDeleteResponse,
)
def remove_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_current_user),
):
    deleted = database_call(
        auth_store.delete_conversation,
        current_user["id"],
        conversation_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"ok": True}


@conversations_router.post(
    "/{conversation_id}/messages",
    response_model=LLMResponse,
)
def create_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    current_user: dict = Depends(require_current_user),
):
    conversation = database_call(
        auth_store.get_conversation,
        current_user["id"],
        conversation_id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    report = conversation["report"]
    context = (
        "You are a helpful research assistant. The current report is a preliminary "
        "framework, not source-verified research. Do not invent citations or claim "
        "that external sources were retrieved. Be clear about uncertainty.\n\n"
        f"Topic: {report['topic']}\n"
        f"Summary: {report['executive_summary']}\n"
        f"Research questions: {' | '.join(report.get('research_questions', []))}"
    )
    history = [
        Message(role=item["role"], content=item["content"])
        for item in conversation["messages"][-10:]
    ]

    database_call(
        auth_store.add_message,
        conversation_id,
        "user",
        request.content,
    )
    try:
        result = llm_gateway.generate(
            LLMRequest(
                provider=request.provider,
                model=request.model,
                messages=[
                    Message(role="system", content=context),
                    *history,
                    Message(role="user", content=request.content),
                ],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                timeout=request.timeout,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    database_call(
        auth_store.add_message,
        conversation_id,
        "assistant",
        result.content,
    )
    return result
