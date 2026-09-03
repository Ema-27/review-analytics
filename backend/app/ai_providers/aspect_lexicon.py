"""
Lessico multilingua (IT/EN/FR/ES) di parole chiave -> aspetto normalizzato,
usato dal provider locale per l'estrazione di aspetti (aspect-based sentiment
"leggero"): individua a quali aspetti di una struttura (colazione, personale,
pulizia, prezzo, ...) fa riferimento ogni frase di una recensione, cosi' da
poter poi calcolare quali aspetti sono i piu' apprezzati o i piu' criticati.

Un sistema di produzione userebbe probabilmente un modello ABSA dedicato
(Aspect-Based Sentiment Analysis) o tecniche di topic modelling; questo
approccio a lessico e' volutamente leggero (nessun modello aggiuntivo da
scaricare), mantiene risultati interpretabili ed e' facilmente estendibile
aggiungendo voci al dizionario.
"""
from __future__ import annotations

ASPECT_KEYWORDS: dict[str, list[str]] = {
    "colazione": ["colazione", "breakfast", "petit-dejeuner", "petit déjeuner", "desayuno"],
    "personale": [
        "personale", "staff", "receptionist", "cameriere", "camerieri", "waiter",
        "employees", "personnel", "empleados", "reception",
    ],
    "pulizia": ["pulizia", "pulito", "cleanliness", "clean", "propreté", "propre", "limpieza", "limpio"],
    "posizione": ["posizione", "location", "position", "emplacement", "ubicacion", "ubicación"],
    "prezzo": [
        "prezzo", "prezzi", "price", "costo", "cost", "expensive", "economico",
        "prix", "cher", "precio", "caro",
    ],
    "camera": ["camera", "stanza", "room", "chambre", "habitacion", "habitación"],
    "wifi": ["wifi", "wi-fi", "internet", "connessione"],
    "cibo": [
        "cibo", "piatto", "piatti", "food", "dish", "cuisine", "nourriture",
        "comida", "plato", "menu", "menù",
    ],
    "servizio": ["servizio", "service", "servicio"],
    "atmosfera": ["atmosfera", "ambience", "ambiance", "atmosphere", "ambiente"],
    "tempi di attesa": [
        "attesa", "aspettato", "waiting", "wait", "queue", "coda", "attente", "espera",
    ],
    "organizzazione": ["organizzazione", "organization", "organisation", "organizacion", "organización"],
    "guida": ["guida", "guide", "tour guide", "guía"],
    "coda": ["coda", "queue", "fila", "line", "file"],
    "valore": ["valore", "value", "worth", "valeur", "valor"],
}


def extract_aspects_from_text(text: str) -> dict[str, str]:
    """Ritorna un dict {aspetto: frase_di_contesto} per ogni aspetto trovato
    nel testo, spezzando il testo in frasi e cercando le keyword del lessico
    (case-insensitive, substring match)."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    found: dict[str, str] = {}
    lowered_sentences = [(s, s.lower()) for s in sentences if s]

    for aspect, keywords in ASPECT_KEYWORDS.items():
        for sentence, lowered in lowered_sentences:
            if any(kw in lowered for kw in keywords):
                found[aspect] = sentence
                break
    return found
