"""
Provider AI di default: analisi + generazione testuale interamente locali e
gratuite, senza alcuna chiave API esterna.

Divisione dei compiti (scelta di efficienza):

  * Sentiment + estrazione aspetti  -> modelli Hugging Face in-process
    (ereditati da HuggingFaceLocalProvider): sono classificatori piccoli e
    veloci, adatti a essere chiamati centinaia di volte durante l'ingestion.

  * Generazione di sintesi / confronto competitivo / suggerimenti  -> un LLM
    instruction-tuned quantizzato (default: qwen2.5:1.5b, configurabile con
    OLLAMA_MODEL) servito da un container **Ollama** dedicato (vedi
    docker-compose.yml). A parita' di vincolo "tutto locale, nessuna API a
    pagamento", la qualita' del testo in italiano e' nettamente superiore a
    quella di flan-t5-base (che, essendo minuscolo, ripeteva il prompt).

Come per gli altri provider, ogni generazione e' comunque ancorata ai fatti
reali calcolati da stats_service e ha una rete di sicurezza a template
(narrative_templates): se il container Ollama non e' raggiungibile, il modello
non e' ancora stato scaricato o l'output non e' utilizzabile, il sistema
restituisce comunque un report coerente basato sui dati, senza errori.

Passare a un altro motore (Claude, OpenAI, ...) resta una questione di
implementare la stessa interfaccia AIProvider e cambiare AI_PROVIDER in .env.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.ai_providers.huggingface_local import HuggingFaceLocalProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Sei un analista di customer experience nel settore turistico. "
    "Rispondi sempre ed esclusivamente in italiano, in prosa discorsiva e "
    "scorrevole (niente elenchi puntati se non esplicitamente richiesto), in "
    "modo concreto e professionale. Attieniti STRETTAMENTE ai dati forniti nel "
    "messaggio dell'utente: non aggiungere dettagli, aggettivi elogiativi, "
    "nazionalita' dei clienti o altri fatti non presenti nei dati. Non "
    "ripetere l'istruzione ricevuta. Concludi sempre le frasi: non lasciare il "
    "testo a meta'."
)

# Tetto di token generati: abbastanza per un report di 4-6 frasi / un confronto
# / 3-4 suggerimenti senza troncare a meta' frase, ma non oltre — su CPU ogni
# token in piu' e' tempo di attesa per l'utente.
_MIN_NUM_PREDICT = 340


class OllamaProvider(HuggingFaceLocalProvider):
    name = "ollama"

    def __init__(self) -> None:
        super().__init__()
        settings = self._settings
        self.model_label = f"{settings.hf_sentiment_model} + ollama:{settings.ollama_model}"
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._model_ready = False

    # ------------------------------------------------------------------
    # Gestione modello: scaricato una tantum e persistito nel volume Docker
    # `ollama_data` (il container ollama-init lo pre-scarica all'avvio; questo
    # e' solo una rete di sicurezza idempotente per il primo utilizzo).
    # ------------------------------------------------------------------
    def _ensure_model(self) -> None:
        if self._model_ready:
            return
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{self._base_url}/api/tags")
            resp.raise_for_status()
            installed = {m.get("name", "") for m in resp.json().get("models", [])}

        base_names = {name.split(":")[0] for name in installed}
        if self._model in installed or self._model.split(":")[0] in base_names:
            self._model_ready = True
            return

        logger.info("Ollama: scarico il modello '%s' (una tantum, alcuni minuti)...", self._model)
        with httpx.Client(timeout=self._settings.ollama_pull_timeout_secs) as client:
            resp = client.post(
                f"{self._base_url}/api/pull",
                json={"name": self._model, "stream": False},
            )
            resp.raise_for_status()
        self._model_ready = True

    def warm_up(self) -> None:
        """Carica il modello LLM nella RAM di Ollama (una generazione minima),
        cosi' la prima richiesta reale dell'utente non paga il caricamento."""
        try:
            self._ensure_model()
            with httpx.Client(timeout=120) as client:
                client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": "ok"}],
                        "stream": False,
                        "options": {"num_predict": 1},
                        "keep_alive": "30m",
                    },
                )
            logger.info("Modello LLM Ollama '%s' pre-caricato.", self._model)
        except Exception:  # pragma: no cover - warmup best-effort
            logger.warning("Pre-caricamento LLM Ollama non riuscito (verra' caricato al primo uso).")

    # ------------------------------------------------------------------
    # Override del solo passo di generazione testuale: le tre funzioni
    # generate_summary / generate_comparison / generate_suggestions (con la
    # costruzione dei "fatti" e il fallback a template) restano quelle del
    # provider padre e chiamano questo metodo.
    # ------------------------------------------------------------------
    def _generate(self, prompt: str, max_new_tokens: int = 200) -> Optional[str]:
        try:
            self._ensure_model()
            with httpx.Client(timeout=self._settings.ollama_timeout_secs) as client:
                resp = client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": max(max_new_tokens, _MIN_NUM_PREDICT),
                            # Leggera penalita' alle ripetizioni (valori troppo
                            # alti degradano la fluidita' dei modelli piccoli).
                            "repeat_penalty": 1.15,
                        },
                    },
                )
                resp.raise_for_status()
                content = (resp.json().get("message") or {}).get("content", "").strip()
                return content or None
        except Exception:  # pragma: no cover - difensivo: si ricade sui template
            logger.exception("Generazione via Ollama fallita, uso narrativa basata su template")
            return None
