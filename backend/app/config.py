from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://dsa:dsa@localhost:5432/algolog"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"

    # Supabase auth: JWT secret from Project Settings > API > JWT Secret (HS256).
    # ponytail: HS256 shared-secret verify. If you switch Supabase to asymmetric
    # signing keys, move deps.py to JWKS fetch instead.
    SUPABASE_JWT_SECRET: str = "change-me"
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    DIGEST_TO_EMAIL: str = ""

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    class Config:
        env_file = ".env"


settings = Settings()
