import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Gerekli ortam degiskeni bulunamadi: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    database_host: str = "127.0.0.1"
    database_port: int = 5433
    database_name: str = "casemarket_db"
    database_user: str = "casemarket_user"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    @property
    def postgres_password(self) -> str:
        return _required_environment_variable("POSTGRES_PASSWORD")

    @property
    def jwt_secret_key(self) -> str:
        return _required_environment_variable("JWT_SECRET_KEY")


settings = Settings()
