import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from app import config
from app.database import auth_store
from app.database.errors import database_call


auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)

ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_LIFETIME = timedelta(days=30)
ACCESS_TOKEN_SECONDS = int(ACCESS_TOKEN_LIFETIME.total_seconds())
_PASSWORD_SCRYPT_N = 2**14
_PASSWORD_SCRYPT_R = 8
_PASSWORD_SCRYPT_P = 1


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


class SignupRequest(AuthRequest):
    full_name: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(min_length=7, max_length=32)
    country: str = Field(min_length=1, max_length=100)

    @field_validator("full_name", "country")
    @classmethod
    def normalize_profile_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field is required.")
        return normalized

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = value.strip()
        digits = re.sub(r"\D", "", normalized)
        if (
            not re.fullmatch(r"\+?[0-9().\-\s]{7,32}", normalized)
            or not 7 <= len(digits) <= 15
            or normalized.count("+") > 1
            or ("+" in normalized and not normalized.startswith("+"))
        ):
            raise ValueError("Enter a phone number with 7 to 15 digits.")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


def _require_auth_configuration() -> None:
    if not config.auth_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Set DATABASE_URL to your MySQL database.",
        )


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_PASSWORD_SCRYPT_N,
        r=_PASSWORD_SCRYPT_R,
        p=_PASSWORD_SCRYPT_P,
        dklen=64,
    )
    return (
        f"scrypt${_PASSWORD_SCRYPT_N}${_PASSWORD_SCRYPT_R}${_PASSWORD_SCRYPT_P}"
        f"${salt.hex()}${digest.hex()}"
    )


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = stored_hash.split("$")
        if (
            algorithm != "scrypt"
            or int(n) != _PASSWORD_SCRYPT_N
            or int(r) != _PASSWORD_SCRYPT_R
            or int(p) != _PASSWORD_SCRYPT_P
        ):
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=_PASSWORD_SCRYPT_N,
            r=_PASSWORD_SCRYPT_R,
            p=_PASSWORD_SCRYPT_P,
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_session(user: dict[str, Any]) -> dict[str, Any]:
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    now = _utc_now()
    database_call(
        auth_store.create_session,
        user["id"],
        access_token,
        refresh_token,
        now + ACCESS_TOKEN_LIFETIME,
        now + REFRESH_TOKEN_LIFETIME,
    )
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name", ""),
            "phone_number": user.get("phone_number", ""),
            "country": user.get("country", ""),
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_SECONDS,
    }


def _invalid_session() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Your session is invalid or has expired. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


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

    user = database_call(
        auth_store.find_user_by_access_token,
        credentials.credentials,
    )
    if user is None:
        raise _invalid_session()
    return user


@auth_router.get("/config")
def auth_config() -> dict[str, bool]:
    return {"configured": config.auth_is_configured()}


@auth_router.post("/signup")
def signup(request: SignupRequest) -> dict[str, Any]:
    _require_auth_configuration()
    user = database_call(
        auth_store.create_user,
        request.email,
        _password_hash(request.password),
        request.full_name,
        request.phone_number,
        request.country,
    )
    if user is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    return _new_session(user)


@auth_router.post("/login")
def login(request: AuthRequest) -> dict[str, Any]:
    _require_auth_configuration()
    user = database_call(auth_store.find_user_by_email, request.email)
    if user is None or not _verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    return _new_session(user)


@auth_router.post("/refresh")
def refresh(request: RefreshRequest) -> dict[str, Any]:
    _require_auth_configuration()
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    now = _utc_now()
    user = database_call(
        auth_store.rotate_session,
        request.refresh_token,
        access_token,
        refresh_token,
        now + ACCESS_TOKEN_LIFETIME,
        now + REFRESH_TOKEN_LIFETIME,
    )
    if user is None:
        raise _invalid_session()
    return {
        "user": user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_SECONDS,
    }


@auth_router.get("/me")
def me(
    current_user: dict[str, Any] = Depends(require_current_user),
) -> dict[str, Any]:
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user.get("full_name", ""),
        "phone_number": current_user.get("phone_number", ""),
        "country": current_user.get("country", ""),
    }


@auth_router.post("/logout", dependencies=[Depends(require_current_user)])
def logout(
    authorization: str | None = Header(default=None),
) -> dict[str, bool]:
    if authorization is None:
        raise HTTPException(status_code=401, detail="A session is required.")
    token = authorization.partition(" ")[2]
    database_call(auth_store.revoke_access_token, token)
    return {"ok": True}
