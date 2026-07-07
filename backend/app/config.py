from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://dsa:dsa@localhost:5432/algolog"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "phi3"

    # Supabase auth: project uses asymmetric JWT signing keys (ES256)
    SUPABASE_PROJECT_URL: str = "https://zgeymiyigfcyowdyrdln.supabase.co/"
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
