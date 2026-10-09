import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import create_app
from app.config import Config
from app.middleware.auth import TokenVerifier
from tests.fakes import FakeRepo, FakeSender

URL = "https://proj.supabase.co"
ALICE, BOB, CAROL = ("00000000-0000-0000-0000-0000000000a1", "00000000-0000-0000-0000-0000000000b2",
                      "00000000-0000-0000-0000-0000000000c3")
PRIVATE = ec.generate_private_key(ec.SECP256R1())


class StubJwks:
    """Pretends to be Supabase's JWKS: hands back our test public key."""
    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=PRIVATE.public_key())


def make_token(sub=ALICE, exp_in=3600, aud="authenticated", iss=f"{URL}/auth/v1", role="authenticated", key=None, alg="ES256", **extra):
    payload = {"sub": sub, "aud": aud, "iss": iss, "role": role, "email": "a@example.test",
               "exp": int(time.time()) + exp_in, **extra}
    return jwt.encode(payload, key or PRIVATE, algorithm=alg, headers={"kid": "k1"})


def auth(user=ALICE):
    return {"Authorization": f"Bearer {make_token(user)}"}


@pytest.fixture
def repo():
    r = FakeRepo()
    r.add_user(ALICE, "alice@example.test", "Alice")
    r.add_user(BOB, "bob@example.test", "Bob")
    r.add_user(CAROL, "carol@example.test", "Carol")
    return r


@pytest.fixture
def sender():
    return FakeSender()


@pytest.fixture
def app(repo, sender):
    cfg = Config(supabase_url=URL, supabase_service_role_key="x", cron_secret="s3cret",
                 frontend_url="http://localhost:3000", cors_origins=("http://localhost:3000",))
    return create_app(cfg, repo=repo, sender=sender, verifier=TokenVerifier(URL, jwks_client=StubJwks()))


@pytest.fixture
def client(app):
    return app.test_client()
