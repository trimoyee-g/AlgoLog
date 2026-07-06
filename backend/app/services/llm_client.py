"""
Thin wrapper around the local Ollama HTTP API.
Runs fully free/local via Docker - no API key needed.
Pull a model first: docker exec -it algolog-ollama ollama pull phi3
"""
import httpx

from app.config import settings


def generate(prompt: str, system: str = "", timeout: float = 60.0) -> str:
    """Single-shot generation call to Ollama. Returns plain text."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
    }
    try:
        resp = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except httpx.HTTPError as e:
        # Ollama not running / model not pulled yet - fail soft, don't crash the endpoint
        return f"[LLM unavailable: {e}. Is Ollama running with the model pulled?]"
