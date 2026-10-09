"""Configuration read from environment variables. No secret is ever hard-coded or logged."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    frontend_url: str = "http://localhost:3000"
    cors_origins: tuple = ("http://localhost:3000",)
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_sender_email: str = ""
    cron_secret: str = ""
    env: str = "development"

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        get = lambda k, d="": os.environ.get(k, d).strip()
        origins = tuple(o.strip() for o in get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip())
        return cls(
            supabase_url=get("SUPABASE_URL").rstrip("/"),
            supabase_service_role_key=get("SUPABASE_SERVICE_ROLE_KEY"),
            frontend_url=get("FRONTEND_URL", "http://localhost:3000").rstrip("/"),
            cors_origins=origins,
            gmail_client_id=get("GMAIL_CLIENT_ID"),
            gmail_client_secret=get("GMAIL_CLIENT_SECRET"),
            gmail_refresh_token=get("GMAIL_REFRESH_TOKEN"),
            gmail_sender_email=get("GMAIL_SENDER_EMAIL"),
            cron_secret=get("CRON_SECRET"),
            env=get("FLASK_ENV", "development"),
        )

    @property
    def gmail_configured(self) -> bool:
        return all([self.gmail_client_id, self.gmail_client_secret, self.gmail_refresh_token, self.gmail_sender_email])

    def validate(self) -> None:
        """Fail fast at startup. Only variable NAMES are reported, never values."""
        missing = [n for n, v in [("SUPABASE_URL", self.supabase_url),
                                  ("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_role_key)] if not v]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        if self.env == "production" and "*" in self.cors_origins:
            raise RuntimeError("CORS_ORIGINS must list explicit origins in production")
