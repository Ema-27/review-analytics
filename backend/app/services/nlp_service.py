"""
Factory per il provider AI attivo. Centralizza la scelta dell'implementazione
concreta (vedi app/ai_providers/) in base alla configurazione, cosi' che il
resto del sistema (ingestion_service, router `ai`) dipenda solo
dall'interfaccia astratta AIProvider e possa essere ri-configurato via env var
senza modifiche al codice (vedi AI_PROVIDER in app/config.py).
"""
from __future__ import annotations

from functools import lru_cache

from app.ai_providers.base import AIProvider
from app.config import get_settings


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "mock":
        from app.ai_providers.mock_provider import MockAIProvider

        return MockAIProvider()

    if settings.ai_provider == "huggingface_local":
        from app.ai_providers.huggingface_local import HuggingFaceLocalProvider

        return HuggingFaceLocalProvider()

    # default: 'ollama' (sentiment/aspetti via Hugging Face, generazione via
    # LLM instruct locale servito dal container Ollama)
    from app.ai_providers.ollama_provider import OllamaProvider

    return OllamaProvider()
