"""AUTHENTICATION: prove who is calling, using the Supabase access token (a JWT).

We never write our own signature maths. PyJWT checks the signature against the public keys
Supabase publishes at  <SUPABASE_URL>/auth/v1/.well-known/jwks.json  and also checks
issuer (iss), audience (aud) and expiry (exp). Only asymmetric algorithms are allowed, which
blocks the classic "algorithm confusion" attack (an attacker re-signing a token with HS256).
"""
import functools
import logging
from dataclasses import dataclass

import jwt
from flask import current_app, g, request
from jwt import PyJWKClient

from app.utils.errors import ApiError
from app.utils.ids import parse_uuid

log = logging.getLogger(__name__)
ALLOWED_ALGORITHMS = ["ES256", "RS256"]


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    full_name: str | None
    avatar_url: str | None


class TokenVerifier:
    def __init__(self, supabase_url: str, jwks_client=None):
        self.issuer = f"{supabase_url}/auth/v1"
        self.jwks_client = jwks_client or PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json", cache_keys=True, lifespan=3600, timeout=5
        )

    def verify(self, token: str) -> CurrentUser:
        try:
            key = self.jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token, key, algorithms=ALLOWED_ALGORITHMS, audience="authenticated", issuer=self.issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            raise ApiError(401, "token_expired", "Your session has expired. Please sign in again.") from None
        except jwt.PyJWKClientConnectionError:
            log.error("Could not reach Supabase JWKS endpoint")
            raise ApiError(503, "auth_unavailable", "Authentication service is temporarily unavailable") from None
        except jwt.PyJWTError:
            raise ApiError(401, "invalid_token", "Invalid authentication token") from None
        if claims.get("role") != "authenticated":
            raise ApiError(401, "invalid_token", "Invalid authentication token")
        try:
            user_id = parse_uuid(claims["sub"], "sub")
        except ApiError:
            raise ApiError(401, "invalid_token", "Invalid authentication token") from None
        meta = claims.get("user_metadata") or {}
        return CurrentUser(
            id=user_id,
            email=claims.get("email", ""),
            full_name=meta.get("full_name") or meta.get("name"),
            avatar_url=meta.get("avatar_url") or meta.get("picture"),
        )


def require_auth(view):
    """Decorator: reject the request with 401 unless it carries a valid Bearer token."""
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise ApiError(401, "missing_token", "Authentication required")
        g.user = current_app.extensions["token_verifier"].verify(token.strip())
        return view(*args, **kwargs)
    return wrapper
