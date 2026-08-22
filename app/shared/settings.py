from dataclasses import dataclass
from urllib.parse import quote
import os


def _build_default_database_url() -> str:
    """Monta a URL padrão do PostgreSQL a partir de variáveis POSTGRES_*.

    Permite configurar o banco em partes (host, porta, usuário, senha, base)
    sem precisar montar manualmente uma URL completa. Caso `DATABASE_URL`
    esteja definida, ela tem precedência e é usada diretamente.

    Usuário e senha passam por `quote()` (percent-encoding) antes de entrar
    na URL — sem isso, uma senha com caracteres especiais (ex.: a senha do
    RDS é gerada aleatoriamente e pode conter `[`, `]`, `#`, `@`, `:`, `/`)
    quebra qualquer parser de URL estrito. O `create_engine` do SQLAlchemy
    tem um parser próprio, mais tolerante, que não se importa — mas o
    `urllib.parse.urlparse` do stdlib (usado em `get_safe_database_url`,
    abaixo) interpreta `[...]` como um endereço IPv6 literal e falha com
    "Invalid IPv6 URL". Codificar aqui resolve pra qualquer consumidor,
    não só o que quebrou primeiro.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = quote(os.getenv("POSTGRES_USER", "oficina"), safe="")
    password = quote(os.getenv("POSTGRES_PASSWORD", "oficina"), safe="")
    db = os.getenv("POSTGRES_DB", "oficina_mecanica")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    admin_username: str
    admin_password: str
    public_base_url: str
    # SMTP / e-mail
    smtp_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_from: str
    smtp_username: str
    smtp_password: str


settings = Settings(
    app_name="Oficina Mecânica FIAP API",
    database_url=os.getenv("DATABASE_URL", _build_default_database_url()),
    jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
    admin_username=os.getenv("ADMIN_USERNAME", "admin"),
    admin_password=os.getenv("ADMIN_PASSWORD", "Admin@123"),
    public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
    # SMTP
    smtp_enabled=os.getenv("SMTP_ENABLED", "false").lower() == "true",
    smtp_host=os.getenv("SMTP_HOST", "localhost"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_from=os.getenv("SMTP_FROM", "noreply@oficina.local"),
    smtp_username=os.getenv("SMTP_USERNAME", ""),
    smtp_password=os.getenv("SMTP_PASSWORD", ""),
)
