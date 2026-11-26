import logging
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)
_T = TypeVar("_T")


def database_call(operation: Callable[..., _T], *args: Any) -> _T:
    try:
        return operation(*args)
    except SQLAlchemyError as error:
        logger.exception("Database operation failed.")
        raise HTTPException(
            status_code=503,
            detail="The database is unavailable. Check the server logs and database connection.",
        ) from error
