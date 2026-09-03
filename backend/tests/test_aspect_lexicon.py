from app.ai_providers.aspect_lexicon import extract_aspects_from_text


def test_extracts_known_aspect_italian():
    text = "La colazione era ottima ma il personale poco cortese."
    found = extract_aspects_from_text(text)
    assert "colazione" in found
    assert "personale" in found


def test_extracts_known_aspect_english():
    text = "The room was clean but the wifi did not work at all."
    found = extract_aspects_from_text(text)
    assert "camera" in found
    assert "wifi" in found


def test_no_aspect_found_returns_empty_dict():
    text = "Un testo qualsiasi senza riferimenti specifici."
    assert extract_aspects_from_text(text) == {}
