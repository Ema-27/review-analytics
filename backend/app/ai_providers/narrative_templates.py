"""
Costruzione di narrazioni testuali strutturate a partire dalle statistiche
calcolate da `app/services/stats_service.py`.

Queste funzioni svolgono due ruoli nel sistema:

1. Forniscono il "contesto fattuale" (fatti, numeri, esempi reali) che viene
   iniettato nei prompt del modello generativo (vedi huggingface_local.py),
   cosi' che il testo generato dall'AI sia ancorato ai dati reali e non
   "allucini" statistiche inventate.
2. Fungono da rete di sicurezza (graceful degradation): se il modello
   generativo locale non e' disponibile, fallisce o produce un output vuoto o
   troppo corto, il sistema restituisce comunque all'utente un report
   testuale coerente e leggibile costruito da questi template, invece di un
   errore. Questo e' un requisito importante per una demo affidabile.
"""
from __future__ import annotations

from typing import Any, Optional


def is_low_quality_generation(text: Optional[str], prompt: str) -> bool:
    """Rileva quando l'output di un modello generativo NON e' utilizzabile e
    conviene ricadere sul report basato su template.

    I modelli locali piccoli a volte, invece di seguire l'istruzione, ricopiano
    il prompt o entrano in loop ripetendo frasi: l'output supererebbe un banale
    controllo di lunghezza ma sarebbe inutile. Qui si controllano: lunghezza
    minima, eco del prompt (n-gram gia' presenti nell'istruzione), poverta'
    lessicale e ripetizione di frasi (4-gram duplicati).
    """
    if not text:
        return True

    normalized = " ".join(text.lower().split())
    if len(normalized) < 60:
        return True

    words = normalized.split()
    if len(words) < 15:
        return True

    # Eco del prompt: quante sequenze di 6 parole dell'output compaiono
    # gia' testualmente nell'istruzione/nei dati passati al modello.
    prompt_normalized = " ".join(prompt.lower().split())
    six_grams = [" ".join(words[i : i + 6]) for i in range(len(words) - 5)]
    if six_grams:
        echoed_ratio = sum(1 for g in six_grams if g in prompt_normalized) / len(six_grams)
        if echoed_ratio > 0.35:
            return True

    # Poverta' lessicale: testo che ripete poche parole (loop degenerato).
    if len(set(words)) / len(words) < 0.4:
        return True

    # Ripetizione di frasi/paragrafi: modelli piccoli a volte generano lo stesso
    # 4-gram piu' volte (es. "un sistema di ritirata immediata ..." x3).
    four_grams = [" ".join(words[i : i + 4]) for i in range(len(words) - 3)]
    if four_grams:
        unique_ratio = len(set(four_grams)) / len(four_grams)
        if unique_ratio < 0.7:
            return True

    return False


def build_summary_facts(stats: dict[str, Any]) -> str:
    prop = stats["property"]
    top_pos = [a for a in stats["top_aspects"] if a["net_sentiment"] > 0][:3]
    top_neg = [a for a in stats["top_aspects"] if a["net_sentiment"] < 0][:3]

    lines = [
        f"Struttura: {prop.name} ({prop.type.value}), {prop.location.city}, {prop.location.country}.",
        f"Numero recensioni analizzate: {stats['review_count']}.",
        f"Valutazione media: {stats['average_rating']} su 5.",
    ]
    if stats["sentiment_breakdown"]:
        parts = [f"{s['label']}: {s['percentage']}%" for s in stats["sentiment_breakdown"]]
        lines.append("Distribuzione sentiment: " + ", ".join(parts) + ".")
    if top_pos:
        lines.append("Aspetti piu' apprezzati: " + ", ".join(a["aspect"] for a in top_pos) + ".")
    if top_neg:
        lines.append("Aspetti piu' criticati: " + ", ".join(a["aspect"] for a in top_neg) + ".")
    return "\n".join(lines)


def build_summary_fallback_text(stats: dict[str, Any]) -> str:
    prop = stats["property"]
    top_pos = [a for a in stats["top_aspects"] if a["net_sentiment"] > 0][:3]
    top_neg = [a for a in stats["top_aspects"] if a["net_sentiment"] < 0][:3]

    parts = [
        f"{prop.name} ({prop.location.city}) ha raccolto {stats['review_count']} recensioni "
        f"con una valutazione media di {stats['average_rating']} su 5."
    ]
    if top_pos:
        parts.append(
            "Gli aspetti piu' apprezzati dagli utenti risultano essere: "
            + ", ".join(a["aspect"] for a in top_pos) + "."
        )
    if top_neg:
        parts.append(
            "Gli aspetti che raccolgono piu' critiche sono invece: "
            + ", ".join(a["aspect"] for a in top_neg) + "."
        )
    if stats["rating_trend"] and len(stats["rating_trend"]) >= 2:
        first, last = stats["rating_trend"][0], stats["rating_trend"][-1]
        direction = "in miglioramento" if last["average_rating"] >= first["average_rating"] else "in calo"
        parts.append(
            f"L'andamento delle valutazioni nel periodo osservato appare {direction} "
            f"(da {first['average_rating']} a {last['average_rating']})."
        )
    return " ".join(parts)


def build_comparison_facts(stats_list: list[dict[str, Any]], distinguishing: dict[str, list]) -> str:
    lines = []
    for stats in stats_list:
        prop = stats["property"]
        dist = distinguishing.get(prop.id, [])
        dist_txt = ", ".join(f"{d['aspect']} ({d['delta_vs_others']:+.2f})" for d in dist) or "nessuno"
        lines.append(
            f"- {prop.name} [{prop.location.city}]: valutazione media {stats['average_rating']}/5 "
            f"su {stats['review_count']} recensioni; fattori distintivi: {dist_txt}."
        )
    return "\n".join(lines)


def build_comparison_fallback_text(stats_list: list[dict[str, Any]], distinguishing: dict[str, list]) -> str:
    ranked = sorted(stats_list, key=lambda s: s["average_rating"], reverse=True)
    parts = ["Confronto competitivo tra le strutture selezionate:"]
    for stats in ranked:
        prop = stats["property"]
        dist = distinguishing.get(prop.id, [])
        if dist:
            best = [d for d in dist if d["delta_vs_others"] > 0]
            worst = [d for d in dist if d["delta_vs_others"] < 0]
            frag = []
            if best:
                frag.append("si distingue positivamente per " + ", ".join(d["aspect"] for d in best))
            if worst:
                frag.append("risulta piu' debole rispetto alla concorrenza su " + ", ".join(d["aspect"] for d in worst))
            detail = "; ".join(frag)
        else:
            detail = "non emergono fattori nettamente distintivi rispetto alle altre strutture confrontate"
        parts.append(
            f"{prop.name} ({stats['average_rating']}/5, {stats['review_count']} recensioni): {detail}."
        )
    return " ".join(parts)


def build_suggestions_fallback_text(stats: dict[str, Any]) -> str:
    prop = stats["property"]
    top_neg = [a for a in stats["top_aspects"] if a["net_sentiment"] < 0]
    top_neg.sort(key=lambda a: (a["net_sentiment"], -a["mentions"]))

    if not top_neg:
        return (
            f"Le recensioni di {prop.name} non evidenziano criticita' ricorrenti significative. "
            "Si consiglia di mantenere gli standard attuali e monitorare periodicamente i nuovi "
            "feedback per anticipare eventuali cali di soddisfazione."
        )

    parts = [f"Sulla base delle criticita' emerse dalle recensioni di {prop.name}, si suggeriscono le seguenti priorita' operative:"]
    for i, aspect in enumerate(top_neg[:4], start=1):
        parts.append(
            f"{i}) intervenire su '{aspect['aspect']}', menzionato negativamente in "
            f"{aspect['negative']} recensioni su {aspect['mentions']} che ne parlano;"
        )
    parts.append(
        "Si raccomanda di affrontare per prima la criticita' con il maggior numero di menzioni "
        "negative, monitorando poi l'evoluzione del sentiment nelle recensioni successive per "
        "verificare l'efficacia degli interventi."
    )
    return " ".join(parts)
