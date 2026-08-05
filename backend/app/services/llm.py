"""One place that decides which chat model the app talks to.

Gemini when a key is configured, else a local Ollama, else nothing — every caller
already degrades to "no answer, here are the passages", so None is a valid model.
"""
from app.config import settings


def has_llm() -> bool:
    """Whether any chat model is configured. Routing asks this before generating."""
    return bool(settings.GEMINI_API_KEY or settings.OLLAMA_MODEL)


def chat_model(temperature: float = 0.3):
    """Build the configured chat model, or None when there isn't one."""
    if settings.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
        )
    if settings.OLLAMA_MODEL:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )
    return None
