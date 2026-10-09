import jwt
import pytest

from app.middleware.auth import TokenVerifier
from tests.conftest import ALICE, URL, auth, make_token


def test_health_is_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


def test_missing_token_401(client):
    r = client.get("/api/me")
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "missing_token"


def test_malformed_header_401(client):
    assert client.get("/api/me", headers={"Authorization": "Token abc"}).status_code == 401


def test_garbage_token_401(client):
    r = client.get("/api/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "invalid_token"


def test_expired_token_has_distinct_code(client):
    r = client.get("/api/me", headers={"Authorization": f"Bearer {make_token(exp_in=-10)}"})
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "token_expired"


@pytest.mark.parametrize("kw", [{"aud": "other"}, {"iss": "https://evil.example/auth/v1"}, {"role": "anon"}, {"sub": "not-a-uuid"}])
def test_wrong_claims_rejected(client, kw):
    r = client.get("/api/me", headers={"Authorization": f"Bearer {make_token(**kw)}"})
    assert r.status_code == 401


def test_token_signed_by_other_key_rejected(client):
    from cryptography.hazmat.primitives.asymmetric import ec
    other = ec.generate_private_key(ec.SECP256R1())
    r = client.get("/api/me", headers={"Authorization": f"Bearer {make_token(key=other)}"})
    assert r.status_code == 401


def test_hs256_algorithm_confusion_rejected(client):
    token = make_token(key="x" * 40, alg="HS256")
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_jwks_outage_is_503_not_401():
    class Down:
        def get_signing_key_from_jwt(self, t):
            raise jwt.PyJWKClientConnectionError("down")
    from app.utils.errors import ApiError
    with pytest.raises(ApiError) as e:
        TokenVerifier(URL, jwks_client=Down()).verify(make_token())
    assert e.value.status == 503


def test_me_returns_profile_and_ignores_client_supplied_id(client):
    r = client.get("/api/me?user_id=00000000-0000-0000-0000-0000000000b2", headers=auth(ALICE))
    assert r.status_code == 200 and r.get_json()["user"]["id"] == ALICE


def test_me_creates_profile_for_new_user(client, repo):
    new = "00000000-0000-0000-0000-0000000000d4"
    r = client.get("/api/me", headers={"Authorization": f"Bearer {make_token(new)}"})
    assert r.status_code == 200 and new in repo.profiles


def test_assignable_users_lists_only_safe_fields(client):
    users = client.get("/api/users/assignable", headers=auth()).get_json()["users"]
    assert len(users) == 3 and set(users[0]) == {"id", "email", "full_name", "avatar_url"}
    assert client.get("/api/users/assignable").status_code == 401


def test_cors_allows_only_configured_origin(client):
    ok = client.options("/api/tasks", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/tasks", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert "Access-Control-Allow-Origin" not in bad.headers
