
from unittest.mock import Mock, patch

import pytest

from fastapi.testclient import TestClient

from app import config
from app.database import auth_store
from app.main import app
from app.schemas.llm import LLMResponse


client = TestClient(app)


@pytest.fixture
def auth_headers(monkeypatch, tmp_path):
    database_path = tmp_path / "llm.sqlite"
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{database_path}")
    user = auth_store.create_user(
        "researcher@example.com",
        "test-password-hash",
        "Researcher Example",
        "+1 555 123 4567",
        "United States",
    )
    monkeypatch.setattr("app.auth.auth_store.find_user_by_access_token", Mock(return_value=user))
    report = auth_store.create_conversation(
        user["id"],
        {
            "topic": "Climate adaptation",
            "executive_summary": "A preliminary research framework.",
            "research_questions": ["What should be investigated?"],
        },
    )
    return {
        "headers": {"Authorization": "Bearer test-access-token"},
        "conversation_id": report["conversation_id"],
    }


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_providers():
    response = client.get("/api/v1/llm/providers")

    assert response.status_code == 200

    providers = response.json()["providers"]

    assert any(
        provider["name"] == "openai"
        for provider in providers
    )

    assert any(
        provider["name"] == "ollama"
        for provider in providers
    )


@patch("app.conversations.llm_gateway.generate")
def test_llm_chat_endpoint(mock_generate, auth_headers):
    mock_generate.return_value = LLMResponse(
        provider="ollama",
        model="llama3.1",
        content="Hello from a test model!",
        finish_reason="stop",
        prompt_tokens=10,
        completion_tokens=8,
        total_tokens=18,
        latency_seconds=0.5,
        request_id="test-request-id",
    )

    response = client.post(
        f"/api/v1/conversations/{auth_headers['conversation_id']}/messages",
        json={
            "provider": "ollama",
            "model": "llama3.1",
            "content": "Hello!",
        },
        headers=auth_headers["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["provider"] == "ollama"
    assert data["model"] == "llama3.1"
    assert data["content"] == "Hello from a test model!"


def test_invalid_llm_request(auth_headers):
    response = client.post(
        f"/api/v1/conversations/{auth_headers['conversation_id']}/messages",
        json={
            "provider": "ollama",
            "model": "llama3.1",
            "content": "",
        },
        headers=auth_headers["headers"],
    )

    assert response.status_code == 422
