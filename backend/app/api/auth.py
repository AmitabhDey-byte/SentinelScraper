"""Local operator boundary for expensive Bright Data control actions."""

import hmac

from fastapi import Header, HTTPException, status

from app.config import settings


def current_user_id(
    x_sentinelscrape_operator: str | None = Header(default=None),
    x_sentinelscrape_demo_user: str | None = Header(default=None),
) -> str:
    """Allow local operation, require a server-side operator token in production."""

    if settings.app_env.casefold() != "production":
        return x_sentinelscrape_demo_user or "local-observer"
    if settings.operations_api_token and x_sentinelscrape_operator and hmac.compare_digest(
        settings.operations_api_token, x_sentinelscrape_operator
    ):
        return "operator"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Operator token required")
