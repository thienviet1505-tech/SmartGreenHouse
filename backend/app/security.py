import secrets

from fastapi import Header, HTTPException

from .config import settings


def _same(a: str | None, b: str | None) -> bool:
    return secrets.compare_digest((a or "").encode(), (b or "").encode())


def dashboard_token_ok(token: str | None) -> bool:
    """If DASHBOARD_TOKEN is empty, authentication is disabled (LAN dev only)."""
    if not settings.dashboard_token:
        return True
    return _same(token, settings.dashboard_token)


def gateway_token_ok(token: str | None) -> bool:
    return _same(token, settings.gateway_token)


async def require_dashboard_token(authorization: str | None = Header(default=None)):
    scheme, _, value = (authorization or "").partition(" ")
    token = value.strip() if scheme.lower() == "bearer" else ""
    if not dashboard_token_ok(token):
        raise HTTPException(status_code=401, detail="Invalid or missing access token")
