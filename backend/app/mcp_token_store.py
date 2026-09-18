"""Shared refresh-token storage for mcp_login.py and mcp_server.py."""
import os
from pathlib import Path

TOKEN_FILE = Path.home() / ".algolog" / "mcp_refresh_token"


def load() -> str:
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    return os.environ.get("SUPABASE_REFRESH_TOKEN", "").strip()


def save(token: str) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)
