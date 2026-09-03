"""
Genera il dataset di esempio (fallback) usato quando Apify non e' configurato o
non e' raggiungibile, cosi' che l'applicazione funzioni sempre anche offline e
senza credenziali esterne.

Il dataset e' sintetico ma costruito con template realistici multilingua
(italiano, inglese, francese, spagnolo) e con menzioni esplicite di "aspetti"
(colazione, personale, pulizia, prezzo, cibo, coda, ...) cosi' da poter
dimostrare in modo credibile le funzionalita' di sentiment/aspect analysis
senza dipendere da servizi esterni durante lo sviluppo o la correzione.

Uso:
    python scripts/generate_sample_dataset.py
Produce:
    app/data/sample_reviews.json
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "sample_reviews.json"

PROPERTIES = [
    # (name, type, city, country, category)
    ("Grand Hotel Plaza", "hotel", "Roma", "Italia", "4 stelle"),
    ("Hotel Vista Mare", "hotel", "Napoli", "Italia", "3 stelle"),
    ("Hotel Riviera Barcelona", "hotel", "Barcellona", "Spagna", "4 stelle"),
    ("Le Petit Palais Hotel", "hotel", "Parigi", "Francia", "4 stelle"),
    ("Trattoria da Enzo", "restaurant", "Roma", "Italia", "Cucina romana"),
    ("La Terrazza sul Golfo", "restaurant", "Napoli", "Italia", "Pesce"),
    ("Bistro Le Marais", "restaurant", "Parigi", "Francia", "Cucina francese"),
    ("Tapas & Vino", "restaurant", "Barcellona", "Spagna", "Tapas"),
    ("Colosseo - Tour Guidato", "attraction", "Roma", "Italia", "Tour storico"),
    ("Museo Archeologico Nazionale", "attraction", "Napoli", "Italia", "Museo"),
    ("Sagrada Familia - Skip the Line", "attraction", "Barcellona", "Spagna", "Monumento"),
    ("Musee du Louvre - Visita Guidata", "attraction", "Parigi", "Francia", "Museo"),
]

ASPECTS = {
    "hotel": ["colazione", "personale", "pulizia", "posizione", "prezzo", "camera", "wifi"],
    "restaurant": ["cibo", "servizio", "prezzo", "atmosfera", "tempi di attesa"],
    "attraction": ["organizzazione", "guida", "prezzo", "coda", "valore"],
}

# Template per lingua: {pos}/{neg}/{neu} frasi che citano un aspetto, combinabili.
TEMPLATES = {
    "it": {
        "pos": [
            "Esperienza fantastica, {aspect} davvero eccellente.",
            "Siamo rimasti molto soddisfatti, soprattutto per {aspect}.",
            "Consigliatissimo, {aspect} sopra le aspettative.",
            "Tornerei sicuramente, {aspect} impeccabile.",
        ],
        "neg": [
            "Purtroppo {aspect} ci ha deluso parecchio.",
            "Non torneremmo, soprattutto per {aspect} scadente.",
            "{aspect} lascia molto a desiderare.",
            "Esperienza sotto le aspettative a causa di {aspect}.",
        ],
        "neu": [
            "Esperienza nella media, {aspect} nella norma.",
            "Niente di eccezionale ma {aspect} accettabile.",
        ],
    },
    "en": {
        "pos": [
            "Fantastic experience, the {aspect} was truly excellent.",
            "We were very happy, especially with the {aspect}.",
            "Highly recommended, {aspect} exceeded expectations.",
            "Would definitely come back, {aspect} was flawless.",
        ],
        "neg": [
            "Unfortunately the {aspect} was quite disappointing.",
            "We wouldn't come back, mainly because of the poor {aspect}.",
            "The {aspect} leaves a lot to be desired.",
            "Below expectations because of the {aspect}.",
        ],
        "neu": [
            "Average experience, {aspect} was okay.",
            "Nothing special but the {aspect} was acceptable.",
        ],
    },
    "fr": {
        "pos": [
            "Experience fantastique, {aspect} vraiment excellent.",
            "Nous etions tres satisfaits, surtout pour {aspect}.",
        ],
        "neg": [
            "Malheureusement {aspect} nous a beaucoup decu.",
            "{aspect} laisse a desirer.",
        ],
        "neu": ["Experience moyenne, {aspect} correct."],
    },
    "es": {
        "pos": [
            "Experiencia fantastica, {aspect} realmente excelente.",
            "Muy satisfechos, sobre todo con {aspect}.",
        ],
        "neg": [
            "Lamentablemente {aspect} nos decepciono bastante.",
            "{aspect} deja mucho que desear.",
        ],
        "neu": ["Experiencia normal, {aspect} aceptable."],
    },
}

LANG_WEIGHTS = [("it", 0.45), ("en", 0.35), ("fr", 0.10), ("es", 0.10)]
AUTHORS = [
    "Marco_R", "Giulia89", "TravelWithMe", "Sofia_L", "JohnD_Traveler", "AnnaK",
    "Pierre_M", "Laura_S", "TheFoodie23", "GlobeTrotterX", "Elena_V", "Carlos_M",
    "Emma_W", "LucaB", "MariaP", "TomH_Reviews",
]


def _sample_rating(sentiment: str) -> float:
    if sentiment == "pos":
        return random.choice([4.0, 4.5, 5.0, 5.0])
    if sentiment == "neg":
        return random.choice([1.0, 1.5, 2.0, 2.5])
    return random.choice([3.0, 3.5])


def _pick_language() -> str:
    r = random.random()
    acc = 0.0
    for lang, w in LANG_WEIGHTS:
        acc += w
        if r <= acc:
            return lang
    return "it"


def generate_review_text(prop_type: str, sentiment: str, lang: str) -> str:
    aspects = random.sample(ASPECTS[prop_type], k=random.choice([1, 2]))
    sentences = []
    for asp in aspects:
        tmpl = random.choice(TEMPLATES[lang][sentiment])
        sentences.append(tmpl.format(aspect=asp))
    return " ".join(sentences)


def generate_reviews_for_property(prop_type: str, n: int, start: date, end: date):
    reviews = []
    span = (end - start).days
    for i in range(n):
        sentiment = random.choices(["pos", "neg", "neu"], weights=[0.6, 0.22, 0.18])[0]
        lang = _pick_language()
        text = generate_review_text(prop_type, sentiment, lang)
        review_date = start + timedelta(days=random.randint(0, span))
        reviews.append(
            {
                "external_review_id": f"sample-{i:04d}-{random.randint(1000,9999)}",
                "author": random.choice(AUTHORS),
                "text": text,
                "rating": _sample_rating(sentiment),
                "language": lang,
                "review_date": review_date.isoformat(),
            }
        )
    reviews.sort(key=lambda r: r["review_date"])
    return reviews


def main() -> None:
    dataset = []
    start = date.today() - timedelta(days=730)
    end = date.today() - timedelta(days=1)
    for name, ptype, city, country, category in PROPERTIES:
        n_reviews = random.randint(35, 70)
        dataset.append(
            {
                "name": name,
                "type": ptype,
                "city": city,
                "country": country,
                "category": category,
                "reviews": generate_reviews_for_property(ptype, n_reviews, start, end),
            }
        )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    total_reviews = sum(len(p["reviews"]) for p in dataset)
    print(f"Generato dataset di esempio: {len(dataset)} strutture, {total_reviews} recensioni -> {OUT_PATH}")


if __name__ == "__main__":
    main()
