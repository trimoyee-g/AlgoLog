from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://dsa:dsa@localhost:5432/algolog"

    # Supabase auth: project uses asymmetric JWT signing keys (ES256).
    # Required — no default. A deploy that forgets this must fail at boot rather
    # than silently verify its users' tokens against someone else's project.
    SUPABASE_PROJECT_URL: str
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Public base URL of this backend. The hosted MCP server advertises it as its
    # resource identifier, and Claude checks the token was issued for it — so it must
    # be the URL clients actually reach, not localhost, in any real deployment.
    MCP_PUBLIC_URL: str = "http://localhost:8000"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Optional local LLM (Ollama) that enriches the weekly digest with a
    # personalized paragraph, study tips, and web-searched problems. Empty model
    # disables it — the digest still sends its deterministic content, unchanged.
    OLLAMA_MODEL: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    class Config:
        env_file = ".env"
        extra = "ignore"  # tolerate stale/unknown env vars (e.g. removed OLLAMA_*)


settings = Settings()
