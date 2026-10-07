"""Server configuration (env-driven, pydantic-settings)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; overridable via CASEMAP_SERVER_* env vars."""

    model_config = SettingsConfigDict(
        env_prefix="CASEMAP_SERVER_",
        env_file=None,  # ponytail: env-only by default; explicit > implicit.
        extra="ignore",
    )

    db_url: str = "sqlite:///./casemap.db"
    # ponytail: 127.0.0.1 binds loopback only; use --host 0.0.0.0 at deploy.
    host: str = "127.0.0.1"
    port: int = 8765
    cors_origins: list[str] = ["*"]
    admin_token: str | None = None


def get_settings() -> Settings:
    """Return a fresh Settings instance (no caching — tests override env)."""
    return Settings()
