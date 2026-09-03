"""
Verifica del mapping dell'output dell'Actor Apify `maxcopell/tripadvisor-reviews`
verso il formato interno delle recensioni.

L'item di esempio riproduce la forma reale restituita dall'Actor (campi `lang`,
`title`, `user` come oggetto/None, `publishedDate` in ISO).
"""
from __future__ import annotations

from app.services.apify_service import canonicalize_tripadvisor_url, normalize_apify_item

_REAL_ITEM = {
    "id": "1076165777",
    "url": "https://www.tripadvisor.com/ShowUserReviews-g60763-d208453-r1076165777-x.html",
    "title": "Ottima esperienza",
    "text": "L'hotel è centrale. La colazione ha tutto. Personale gentilissimo.",
    "lang": "it",
    "publishedDate": "2026-09-03",
    "rating": 5,
    "user": None,
}


def test_maps_core_fields():
    out = normalize_apify_item(_REAL_ITEM)
    assert out is not None
    assert out["external_review_id"] == "1076165777"
    assert out["language"] == "it"
    assert out["rating"] == 5.0
    assert out["review_date"] == "2026-09-03"
    assert out["author"] == "Anonimo"
    # il titolo viene anteposto al corpo per l'analisi NLP
    assert out["text"].startswith("Ottima esperienza.")


def test_item_without_text_is_skipped():
    assert normalize_apify_item({"id": "1", "rating": 4}) is None


def test_author_from_nested_user_object():
    out = normalize_apify_item({**_REAL_ITEM, "user": {"name": "Marco P."}})
    assert out["author"] == "Marco P."


def test_bubble_rating_scale_0_50_is_normalized():
    out = normalize_apify_item({**_REAL_ITEM, "rating": 40})
    assert out["rating"] == 4.0


def test_canonicalize_hotelhighlight_url():
    src = (
        "https://www.tripadvisor.it/HotelHighlight-g580200-d1740289-Reviews-"
        "Bed_breakfast_da_Tommy-Vibo_Valentia_Province_of_Vibo_Valentia_Calabria.html"
    )
    out = canonicalize_tripadvisor_url(src)
    assert out.startswith("https://www.tripadvisor.it/Hotel_Review-g580200-d1740289-Reviews-")


def test_canonicalize_leaves_valid_url_untouched():
    src = (
        "https://www.tripadvisor.com/Hotel_Review-g60763-d208453-Reviews-"
        "Hilton_New_York_Times_Square-New_York_City_New_York.html"
    )
    assert canonicalize_tripadvisor_url(src) == src


def test_canonicalize_ignores_non_tripadvisor():
    assert canonicalize_tripadvisor_url("https://example.com/x") == "https://example.com/x"
