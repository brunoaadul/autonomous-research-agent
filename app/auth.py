import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from app import config


auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


class AuthRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("Enter a valid email address.")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


def _require_auth_configuration() -> None:
    if not config.auth_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.",
        )


def _request_supabase(
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    access_token: str | None = None,
) -> dict[str, Any]:
    _require_auth_configuration()
    headers = {"apikey": config.SUPABASE_ANON_KEY}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        response = httpx.request(
            "POST" if payload is not None else "GET",
            f"{config.SUPABASE_URL}/auth/v1/{path}",
            headers=headers,
            json=payload,
            timeout=10.0,
        )
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="The authentication service could not be reached.",
        ) from error

    if not response.is_success:
        try:
            response_data = response.json()
        except ValueError:
            response_data = {}

        if isinstance(response_data, dict):
            detail = (
                response_data.get("msg")
                or response_data.get("message")
                or "Authentication request failed."
            )
        else:
            detail = "Authentication request failed."
        if response.status_code in (401, 403):
            status_code = 401
        elif response.status_code >= 500:
            status_code = 502
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=detail)

    if response.status_code == 204 or not response.content:
        return {}
    try:
        return response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="The authentication service returned an invalid response.",
        ) from error


def _session_response(response: dict[str, Any]) -> dict[str, Any]:
    user = response.get("user") or {}
    return {
        "user": {
            "id": user.get("id"),
            "email": user.get("email"),
        },
        "access_token": response.get("access_token"),
        "refresh_token": response.get("refresh_token"),
        "expires_in": response.get("expires_in"),
    }


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    _require_auth_configuration()
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Sign in to use the research agent.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        response = httpx.get(
            f"{config.SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": config.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {credentials.credentials}",
            },
            timeout=10.0,
        )
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="The authentication service could not be reached.",
        ) from error

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=401,
            detail="Your session is invalid or has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not response.is_success:
        raise HTTPException(
            status_code=502,
            detail="The authentication service could not validate your session.",
        )
    return response.json()


@auth_router.get("/config")
def auth_config() -> dict[str, bool]:
    return {"configured": config.auth_is_configured()}


@auth_router.post("/signup")
def signup(request: AuthRequest) -> dict[str, Any]:
    response = _request_supabase(
        "signup",
        payload=request.model_dump(),
    )
    if "user" not in response:
        response = {"user": response}
    return _session_response(response)


@auth_router.post("/login")
def login(request: AuthRequest) -> dict[str, Any]:
    response = _request_supabase(
        "token?grant_type=password",
        payload=request.model_dump(),
    )
    return _session_response(response)


@auth_router.post("/refresh")
def refresh(request: RefreshRequest) -> dict[str, Any]:
    response = _request_supabase(
        "token?grant_type=refresh_token",
        payload={"refresh_token": request.refresh_token},
    )
    return _session_response(response)


@auth_router.get("/me")
def me(
    current_user: dict[str, Any] = Depends(require_current_user),
) -> dict[str, Any]:
    return {
        "id": current_user.get("id"),
        "email": current_user.get("email"),
    }


@auth_router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    _current_user: dict[str, Any] = Depends(require_current_user),
) -> dict[str, bool]:
    if authorization is None:
        raise HTTPException(status_code=401, detail="A session is required.")
    token = authorization.partition(" ")[2]
    _request_supabase("logout", payload={}, access_token=token)
    return {"ok": True}
