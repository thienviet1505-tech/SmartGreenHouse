from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Smart Greenhouse")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./smart_greenhouse.db")
    simulator_enabled: bool = os.getenv("SIMULATOR_ENABLED", "true").lower() == "true"
    simulator_interval: float = float(os.getenv("SIMULATOR_INTERVAL", "2.0"))
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


settings = Settings()
