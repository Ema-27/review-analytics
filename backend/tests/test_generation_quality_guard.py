"""
Verifica del filtro di qualita' sull'output dei modelli generativi.

Il modello locale piccolo (flan-t5-base) a volte, invece di seguire
l'istruzione, ricopia il prompt: un banale controllo di lunghezza lo
lascerebbe passare. `is_low_quality_generation` deve intercettare questi casi
cosi' che il sistema ricada sul report basato sui dati reali.
"""
from __future__ import annotations

from app.ai_providers.narrative_templates import is_low_quality_generation

PROMPT = (
    "Sei un analista competitivo nel settore turistico. Confronta le seguenti "
    "strutture simili sulla base dei dati reali forniti, evidenziando in "
    "italiano i principali fattori distintivi tra loro (reputazione, servizi, "
    "valutazioni).\n\nDATI:\n- Hotel A [Roma]: valutazione media 4.1/5.\n\nCONFRONTO:"
)


def test_rejects_empty_or_none():
    assert is_low_quality_generation(None, PROMPT) is True
    assert is_low_quality_generation("", PROMPT) is True


def test_rejects_too_short_output():
    assert is_low_quality_generation("Ok.", PROMPT) is True


def test_rejects_prompt_echo():
    echo = (
        "Sei un analista competitivo nel settore turistico. Confronta le "
        "seguenti strutture simili sulla base dei dati reali forniti, "
        "evidenziando in italiano i principali fattori distintivi tra loro."
    )
    assert is_low_quality_generation(echo, PROMPT) is True


def test_rejects_repetitive_loop():
    loop = "molto buono molto buono molto buono molto buono molto buono molto buono molto buono"
    assert is_low_quality_generation(loop, PROMPT) is True


def test_accepts_genuine_analysis():
    good = (
        "Hotel A si posiziona come la struttura piu' solida del gruppo, con una "
        "valutazione media di 4,1 su 5 e recensioni che elogiano soprattutto la "
        "posizione centrale e la cortesia del personale. Rispetto ai competitor "
        "mostra pero' un punto debole ricorrente sui tempi di attesa al "
        "check-in, aspetto su cui gli altri hotel confrontati risultano piu' "
        "efficienti. La reputazione complessiva resta comunque superiore alla "
        "media del confronto."
    )
    assert is_low_quality_generation(good, PROMPT) is False
