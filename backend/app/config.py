from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

# The backend used to ignore .env completely. Load it from the project root.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Smart Greenhouse")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./smart_greenhouse.db")
    simulator_enabled: bool = os.getenv("SIMULATOR_ENABLED", "false").lower() == "true"
    gateway_token: str = os.getenv("GATEWAY_TOKEN", "change-me")
    dashboard_token: str = os.getenv("DASHBOARD_TOKEN", "")
    retention_days: int = int(os.getenv("RETENTION_DAYS", "14"))
    simulator_interval: float = float(os.getenv("SIMULATOR_INTERVAL", "2.0"))
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
