import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app import config
from app.database import auth_store
from app.main import app
from app.schemas.llm import LLMResponse


client = TestClient(app)


@pytest.fixture
def auth_database(tmp_path, monkeypatch):
    database_path = tmp_path / "auth.sqlite"
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{database_path}")


def create_account(email="researcher@example.com", password="secure-passphrase", **profile):
    profile_data = {
        "full_name": "Researcher Example",
        "phone_number": "+1 555 123 4567",
        "country": "United States",
    }
    profile_data.update(profile)
    return client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, **profile_data},
    )


def test_auth_config_reports_missing_database(monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", "")

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


def test_signup_requires_database_configuration(monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", "")

    response = create_account()

    assert response.status_code == 503


def test_signup_login_refresh_and_logout(auth_database):
    signup_response = create_account(email="Researcher@Example.com")

    assert signup_response.status_code == 200
    session = signup_response.json()
    assert session["user"]["email"] == "researcher@example.com"
    assert session["user"]["full_name"] == "Researcher Example"
    assert session["user"]["phone_number"] == "+1 555 123 4567"
    assert session["user"]["country"] == "United States"
    assert session["access_token"]
    assert session["refresh_token"]
    assert session["expires_in"] == 900

    duplicate_response = create_account()
    assert duplicate_response.status_code == 409

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher@example.com", "password": "secure-passphrase"},
    )
    assert login_response.status_code == 200
    login_session = login_response.json()
    assert login_session["user"] == session["user"]

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "researcher@example.com", "password": "wrong-passphrase"},
    )
    assert invalid_login.status_code == 401

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_session["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refreshed_session = refresh_response.json()

    replayed_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_session["refresh_token"]},
    )
    assert replayed_refresh.status_code == 401

    old_access = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_session['access_token']}"},
    )
    assert old_access.status_code == 401

    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed_session['access_token']}"},
    )
    assert current_user.status_code == 200
    assert current_user.json() == session["user"]

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {refreshed_session['access_token']}"},
    )
    assert logout_response.status_code == 200
    assert logout_response.json() == {"ok": True}

    revoked_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed_session['access_token']}"},
    )
    assert revoked_user.status_code == 401


def test_protected_agent_routes_require_a_session(auth_database):
    research_response = client.post("/research", json={"topic": "Climate adaptation"})
    chat_response = client.post(
        "/api/v1/conversations/invalid/messages",
        json={
            "provider": "ollama",
            "model": "llama3.1",
            "content": "Hello",
        },
    )

    assert research_response.status_code == 401
    assert chat_response.status_code == 401


def test_authenticated_research_returns_a_structured_brief(auth_database):
    session = create_account().json()
    response = client.post(
        "/research",
        json={"topic": "Climate adaptation"},
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "Climate adaptation"
    assert data["conversation_id"]
    assert data["status"] == "completed"
    assert data["research_questions"]
    assert data["research_areas"]


def test_conversation_messages_are_persisted_and_owner_scoped(auth_database, monkeypatch):
    first_session = create_account().json()
    second_session = create_account(
        email="another@example.com",
        full_name="Another Researcher",
    ).json()
    first_headers = {"Authorization": f"Bearer {first_session['access_token']}"}
    second_headers = {"Authorization": f"Bearer {second_session['access_token']}"}

    report_response = client.post(
        "/research",
        json={"topic": "Climate adaptation"},
        headers=first_headers,
    )
    conversation_id = report_response.json()["conversation_id"]

    own_conversations = client.get("/api/v1/conversations", headers=first_headers)
    other_conversations = client.get("/api/v1/conversations", headers=second_headers)
    assert own_conversations.status_code == 200
    assert len(own_conversations.json()) == 1
    assert own_conversations.json()[0]["id"] == conversation_id
    assert other_conversations.json() == []

    monkeypatch.setattr(
        "app.conversations.llm_gateway.generate",
        lambda request: LLMResponse(
            provider=request.provider,
            model=request.model,
            content="A stored response.",
            finish_reason="stop",
            prompt_tokens=5,
            completion_tokens=4,
            total_tokens=9,
            latency_seconds=0.1,
            request_id="test-request",
        ),
    )
    message_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={
            "provider": "ollama",
            "model": "llama3.1",
            "content": "What should I investigate first?",
        },
        headers=first_headers,
    )
    assert message_response.status_code == 200

    detail_response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=first_headers,
    )
    assert detail_response.status_code == 200
    assert [message["role"] for message in detail_response.json()["messages"]] == [
        "user",
        "assistant",
    ]
    assert detail_response.json()["messages"][0]["content"] == "What should I investigate first?"

    hidden_detail = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=second_headers,
    )
    hidden_delete = client.delete(
        f"/api/v1/conversations/{conversation_id}",
        headers=second_headers,
    )
    assert hidden_detail.status_code == 404
    assert hidden_delete.status_code == 404

    delete_response = client.delete(
        f"/api/v1/conversations/{conversation_id}",
        headers=first_headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}
    with auth_store._engine().connect() as connection:
        remaining_messages = connection.execute(
            select(auth_store.messages.c.id).where(
                auth_store.messages.c.conversation_id == conversation_id
            )
        ).all()
    assert remaining_messages == []
    deleted_detail = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=first_headers,
    )
    assert deleted_detail.status_code == 404


def test_signup_requires_valid_phone_number(auth_database):
    response = create_account(phone_number="not a phone")

    assert response.status_code == 422


def test_auth_rejects_malformed_email():
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "not-an-email", "password": "secure-passphrase"},
    )

    assert response.status_code == 422
