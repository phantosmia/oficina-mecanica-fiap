from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATABASE_PATH = BASE_DIR / "data" / "oficina_mecanica.db"


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_path: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    admin_username: str
    admin_password: str
    # SMTP / e-mail
    smtp_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_from: str
    smtp_username: str
    smtp_password: str


settings = Settings(
    app_name="Oficina Mecânica FIAP API",
    database_path=os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH)),
    jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
    admin_username=os.getenv("ADMIN_USERNAME", "admin"),
    admin_password=os.getenv("ADMIN_PASSWORD", "Admin@123"),
    # SMTP
    smtp_enabled=os.getenv("SMTP_ENABLED", "false").lower() == "true",
    smtp_host=os.getenv("SMTP_HOST", "localhost"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_from=os.getenv("SMTP_FROM", "noreply@oficina.local"),
    smtp_username=os.getenv("SMTP_USERNAME", ""),
    smtp_password=os.getenv("SMTP_PASSWORD", ""),
)
