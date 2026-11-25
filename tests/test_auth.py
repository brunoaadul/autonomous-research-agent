from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app import config
from app.main import app


client = TestClient(app)


def test_auth_config_reports_missing_supabase(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "")
    monkeypatch.setattr(config, "SUPABASE_ANON_KEY", "")

    response = client.get("/api/v1/auth/config")

    assert response.status_code == 200
    assert response.json() == {"configured": False}


def test_browser_root_serves_the_workspace():
    response = client.get("/", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "Crokuta" in response.text


def test_workspace_static_files_are_served():
    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert "initialize();" in response.text


def test_signup_requires_supabase_configuration(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "")
    monkeypatch.setattr(config, "SUPABASE_ANON_KEY", "")

    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "researcher@example.com", "password": "secure-passphrase"},
    )

    assert response.status_code == 503


def test_signup_returns_only_required_session_fields(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_ANON_KEY", "public-key")
    supabase_response = Mock()
    supabase_response.is_success = True
    supabase_response.json.return_value = {
        "user": {"id": "user-123", "email": "researcher@example.com"},
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
        "provider_token": "must-not-be-returned",
    }

    with patch("app.auth.httpx.request", return_value=supabase_response) as request:
        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "Researcher@Example.com", "password": "secure-passphrase"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "user": {"id": "user-123", "email": "researcher@example.com"},
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 3600,
    }
    assert request.call_args.kwargs["json"]["email"] == "researcher@example.com"


def test_protected_agent_routes_require_a_session(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_ANON_KEY", "public-key")

    research_response = client.post("/research", json={"topic": "Climate adaptation"})
    chat_response = client.post(
        "/api/v1/llm/chat",
        json={
            "provider": "ollama",
            "model": "llama3.1",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert research_response.status_code == 401
    assert chat_response.status_code == 401


def test_authenticated_research_returns_a_structured_brief(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_ANON_KEY", "public-key")
    user_response = Mock()
    user_response.status_code = 200
    user_response.is_success = True
    user_response.json.return_value = {
        "id": "test-user",
        "email": "researcher@example.com",
    }

    with patch("app.auth.httpx.get", return_value=user_response):
        response = client.post(
            "/research",
            json={"topic": "Climate adaptation"},
            headers={"Authorization": "Bearer valid-access-token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "Climate adaptation"
    assert data["status"] == "completed"
    assert data["research_questions"]
    assert data["research_areas"]


def test_auth_rejects_malformed_email():
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "not-an-email", "password": "secure-passphrase"},
    )

    assert response.status_code == 422
