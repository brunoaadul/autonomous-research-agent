import hashlib
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app import config


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(254), nullable=False, unique=True),
    Column("password_hash", String(256), nullable=False),
    Column("created_at", DateTime(), nullable=False),
)

user_profiles = Table(
    "user_profiles",
    metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("full_name", String(120), nullable=False),
    Column("phone_number", String(32), nullable=False),
    Column("country", String(100), nullable=False),
)

sessions = Table(
    "auth_sessions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("access_token_hash", String(64), nullable=False, unique=True),
    Column("refresh_token_hash", String(64), nullable=False, unique=True),
    Column("access_expires_at", DateTime(), nullable=False),
    Column("refresh_expires_at", DateTime(), nullable=False),
    Column("created_at", DateTime(), nullable=False),
)

conversations = Table(
    "conversations",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("title", String(500), nullable=False),
    Column("report", JSON, nullable=False),
    Column("created_at", DateTime(), nullable=False),
    Column("updated_at", DateTime(), nullable=False),
)
Index("ix_conversations_user_updated", conversations.c.user_id, conversations.c.updated_at)

messages = Table(
    "conversation_messages",
    metadata,
    Column("id", String(36), primary_key=True),
    Column(
        "conversation_id",
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("role", String(20), nullable=False),
    Column("content", Text(), nullable=False),
    Column("created_at", DateTime(), nullable=False),
)
Index("ix_conversation_messages_order", messages.c.conversation_id, messages.c.created_at)

_engine_lock = threading.RLock()
_engine_url: str | None = None
_engine_instance: Engine | None = None
_schema_initialized = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _engine() -> Engine:
    global _engine_instance, _engine_url, _schema_initialized

    url = config.DATABASE_URL
    if not url:
        raise RuntimeError("DATABASE_URL is not configured.")

    with _engine_lock:
        if _engine_url != url:
            if _engine_instance is not None:
                _engine_instance.dispose()
            _engine_instance = create_engine(
                url,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
            _engine_url = url
            _schema_initialized = False

        if not _schema_initialized:
            metadata.create_all(_engine_instance)
            _schema_initialized = True

        return _engine_instance


def create_user(
    email: str,
    password_hash: str,
    full_name: str,
    phone_number: str,
    country: str,
) -> dict[str, Any] | None:
    engine = _engine()
    user_id = str(uuid4())
    now = _utc_now()
    user = {
        "id": user_id,
        "email": email,
        "password_hash": password_hash,
        "created_at": now,
    }
    try:
        with engine.begin() as connection:
            connection.execute(insert(users).values(**user))
            connection.execute(
                insert(user_profiles).values(
                    user_id=user_id,
                    full_name=full_name,
                    phone_number=phone_number,
                    country=country,
                )
            )
    except IntegrityError:
        return None
    return {
        "id": user_id,
        "email": email,
        "password_hash": password_hash,
        "full_name": full_name,
        "phone_number": phone_number,
        "country": country,
    }


def find_user_by_email(email: str) -> dict[str, Any] | None:
    with _engine().connect() as connection:
        result = connection.execute(
            select(
                users.c.id,
                users.c.email,
                users.c.password_hash,
                user_profiles.c.full_name,
                user_profiles.c.phone_number,
                user_profiles.c.country,
            )
            .select_from(users.outerjoin(user_profiles, users.c.id == user_profiles.c.user_id))
            .where(
                users.c.email == email,
            )
        ).mappings().first()
    if result is None:
        return None
    user = dict(result)
    user["full_name"] = user["full_name"] or ""
    user["phone_number"] = user["phone_number"] or ""
    user["country"] = user["country"] or ""
    return user


def create_session(
    user_id: str,
    access_token: str,
    refresh_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> None:
    now = _utc_now()
    with _engine().begin() as connection:
        connection.execute(
            delete(sessions).where(sessions.c.refresh_expires_at <= now)
        )
        connection.execute(
            insert(sessions).values(
                id=str(uuid4()),
                user_id=user_id,
                access_token_hash=_token_hash(access_token),
                refresh_token_hash=_token_hash(refresh_token),
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
                created_at=now,
            )
        )


def find_user_by_access_token(access_token: str) -> dict[str, str] | None:
    with _engine().connect() as connection:
        result = connection.execute(
            select(
                users.c.id,
                users.c.email,
                user_profiles.c.full_name,
                user_profiles.c.phone_number,
                user_profiles.c.country,
            )
            .select_from(
                sessions.join(users, sessions.c.user_id == users.c.id).outerjoin(
                    user_profiles,
                    users.c.id == user_profiles.c.user_id,
                )
            )
            .where(
                sessions.c.access_token_hash == _token_hash(access_token),
                sessions.c.access_expires_at > _utc_now(),
            )
        ).mappings().first()
    if result is None:
        return None
    user = dict(result)
    user["full_name"] = user["full_name"] or ""
    user["phone_number"] = user["phone_number"] or ""
    user["country"] = user["country"] or ""
    return user


def rotate_session(
    refresh_token: str,
    access_token: str,
    new_refresh_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> dict[str, str] | None:
    engine = _engine()
    now = _utc_now()
    with engine.begin() as connection:
        result = connection.execute(
            select(
                sessions.c.id,
                sessions.c.refresh_expires_at,
                users.c.id.label("user_id"),
                users.c.email,
                user_profiles.c.full_name,
                user_profiles.c.phone_number,
                user_profiles.c.country,
            )
            .select_from(
                sessions.join(users, sessions.c.user_id == users.c.id).outerjoin(
                    user_profiles,
                    users.c.id == user_profiles.c.user_id,
                )
            )
            .where(
                sessions.c.refresh_token_hash == _token_hash(refresh_token),
            )
            .with_for_update()
        ).mappings().first()
        if result is None or result["refresh_expires_at"] <= now:
            return None

        connection.execute(
            update(sessions)
            .where(sessions.c.id == result["id"])
            .values(
                access_token_hash=_token_hash(access_token),
                refresh_token_hash=_token_hash(new_refresh_token),
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
            )
        )
    return {
        "id": result["user_id"],
        "email": result["email"],
        "full_name": result["full_name"] or "",
        "phone_number": result["phone_number"] or "",
        "country": result["country"] or "",
    }


def revoke_access_token(access_token: str) -> None:
    with _engine().begin() as connection:
        connection.execute(
            delete(sessions).where(
                sessions.c.access_token_hash == _token_hash(access_token)
            )
        )


def create_conversation(user_id: str, report: dict[str, Any]) -> dict[str, Any]:
    conversation_id = str(uuid4())
    now = _utc_now()
    stored_report = {**report, "conversation_id": conversation_id}
    with _engine().begin() as connection:
        connection.execute(
            insert(conversations).values(
                id=conversation_id,
                user_id=user_id,
                title=stored_report["topic"],
                report=stored_report,
                created_at=now,
                updated_at=now,
            )
        )
    return stored_report


def list_conversations(user_id: str) -> list[dict[str, Any]]:
    with _engine().connect() as connection:
        results = connection.execute(
            select(
                conversations.c.id,
                conversations.c.title,
                conversations.c.created_at,
                conversations.c.updated_at,
            )
            .where(conversations.c.user_id == user_id)
            .order_by(conversations.c.updated_at.desc(), conversations.c.id.desc())
        ).mappings()
        return [dict(result) for result in results]


def get_conversation(user_id: str, conversation_id: str) -> dict[str, Any] | None:
    with _engine().connect() as connection:
        result = connection.execute(
            select(
                conversations.c.id,
                conversations.c.title,
                conversations.c.report,
                conversations.c.created_at,
                conversations.c.updated_at,
            ).where(
                conversations.c.id == conversation_id,
                conversations.c.user_id == user_id,
            )
        ).mappings().first()
        if result is None:
            return None

        message_results = connection.execute(
            select(
                messages.c.id,
                messages.c.role,
                messages.c.content,
                messages.c.created_at,
            )
            .where(messages.c.conversation_id == conversation_id)
            .order_by(messages.c.created_at, messages.c.id)
        ).mappings()
        return {
            **dict(result),
            "messages": [dict(message) for message in message_results],
        }


def add_message(conversation_id: str, role: str, content: str) -> dict[str, Any]:
    message = {
        "id": str(uuid4()),
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "created_at": _utc_now(),
    }
    now = _utc_now()
    with _engine().begin() as connection:
        connection.execute(insert(messages).values(**message))
        connection.execute(
            update(conversations)
            .where(conversations.c.id == conversation_id)
            .values(updated_at=now)
        )
    return {key: value for key, value in message.items() if key != "conversation_id"}


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    with _engine().begin() as connection:
        owned_conversation = connection.execute(
            select(conversations.c.id).where(
                conversations.c.id == conversation_id,
                conversations.c.user_id == user_id,
            )
        ).scalar_one_or_none()
        if owned_conversation is None:
            return False
        connection.execute(
            delete(messages).where(messages.c.conversation_id == conversation_id)
        )
        connection.execute(
            delete(conversations).where(
                conversations.c.id == conversation_id,
                conversations.c.user_id == user_id,
            )
        )
    return True
