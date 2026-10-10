"""Settings read from environment variables (or backend/.env). No secrets live in code."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase Postgres. Use the Session pooler string (IPv4, supports transactions).
    database_url: str = ""
    # Only set this to True when using the Transaction pooler (port 6543).
    db_use_nullpool: bool = False

    # Supabase Storage (server-side only; never expose the key to the browser).
    supabase_url: str = ""
    supabase_service_key: str = ""
    storage_bucket: str = "road-images"

    cors_origins: str = "http://localhost:3000"
    # Send the session cookie only over HTTPS. False for local http://localhost; set True when deployed.
    cookie_secure: bool = False
    # Demo/hackathon mode: any email and password logs in, as the role picked on the login page (the account is
    # made on first use). NOT for real use: anyone can become an official. Off unless DEMO_LOGIN=true.
    demo_login: bool = False
    model_path: str = "ml/weights/pothole.pt"
    max_upload_mb: int = 10
    max_video_mb: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
