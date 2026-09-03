"""
Configurazione centralizzata dell'applicazione TourInsight.

Tutte le impostazioni sono lette da variabili d'ambiente (con default sensati
per lo sviluppo locale), seguendo il pattern "12-factor app" cosi' da poter
essere configurate senza modificare il codice sorgente sia in locale che nei
container Docker (vedi docker-compose.yml e .env.example nella root).
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Applicazione ---
    app_name: str = "TourInsight API"
    environment: str = Field(default="development")
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://tourinsight:tourinsight@localhost:5432/tourinsight",
        description="Connection string SQLAlchemy verso PostgreSQL",
    )

    # --- Apify / acquisizione recensioni ---
    apify_api_token: Optional[str] = Field(
        default=None,
        description="Token API Apify (https://apify.com). Se assente il sistema "
        "usa automaticamente il dataset di esempio incluso (fallback).",
    )
    apify_tripadvisor_actor_id: str = Field(
        default="maxcopell/tripadvisor-reviews",
        description="Identificativo dell'Apify Actor usato per lo scraping delle "
        "recensioni Tripadvisor. Sostituibile con altri actor via env var.",
    )
    apify_run_timeout_secs: int = Field(default=120)

    # --- Motore AI/NLP (provider "pluggable") ---
    ai_provider: str = Field(
        default="ollama",
        description="Provider AI attivo: 'ollama' (default, LLM instruct locale "
        "servito da un container Ollama, nessuna chiave richiesta), "
        "'huggingface_local' (solo modelli Hugging Face in-process) oppure "
        "'mock' per test/demo offline rapidissime.",
    )
    hf_sentiment_model: str = Field(default="nlptown/bert-base-multilingual-uncased-sentiment")
    hf_summarization_model: str = Field(default="csebuetnlp/mT5_multilingual_XLSum")
    hf_generation_model: str = Field(default="google/flan-t5-base")
    hf_device: str = Field(default="cpu", description="'cpu' oppure 'cuda' se disponibile")
    ai_models_cache_dir: str = Field(default="/app/model_cache")

    # --- Provider Ollama (generazione testuale) ---
    # Sentiment/aspetti restano sui modelli Hugging Face (veloci); la sola
    # generazione di sintesi/confronto/suggerimenti passa a un LLM instruct
    # quantizzato servito da Ollama: qualita' in italiano nettamente superiore
    # a flan-t5-base, sempre gratuito e offline dopo il primo download.
    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(
        default="gemma2:2b",
        description="Modello Ollama per la generazione. Alternative: 'qwen2.5:3b' "
        "(piu' verboso e lento), 'qwen2.5:0.5b' (rapido ma scarso).",
    )
    ollama_timeout_secs: int = Field(default=180)
    ollama_pull_timeout_secs: int = Field(default=1800)

    # --- CORS ---
    cors_allow_origins: str = Field(default="*")


@lru_cache
def get_settings() -> Settings:
    return Settings()
