import re

from fastapi import Header, HTTPException, status


SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def normalize_session_id(session_id: str) -> str:
    normalized = session_id.strip()
    if not SESSION_ID_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid X-Session-Id header is required.",
        )
    return normalized


def get_session_id(x_session_id: str | None = Header(default=None, alias="X-Session-Id")) -> str:
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Session-Id header.",
        )
    return normalize_session_id(x_session_id)
