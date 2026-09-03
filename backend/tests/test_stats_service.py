from datetime import date

from app.models.models import Location, Property, PropertyType, Review, ReviewSource
from app.services import stats_service
from app.services.nlp_service import get_ai_provider


def _make_property(db_session, name="Test Hotel"):
    loc = Location(city="Roma", country="Italia")
    db_session.add(loc)
    db_session.flush()
    prop = Property(name=name, type=PropertyType.hotel, location_id=loc.id)
    db_session.add(prop)
    db_session.flush()
    return prop


def test_get_property_stats_computes_average_rating(db_session):
    prop = _make_property(db_session)
    provider = get_ai_provider()

    for rating, text in [(5.0, "Fantastic experience, the room was excellent."),
                          (1.0, "Unfortunately the room was quite disappointing.")]:
        review = Review(
            property_id=prop.id,
            source=ReviewSource.manual,
            text=text,
            rating=rating,
            language="en",
            review_date=date.today(),
        )
        db_session.add(review)
        db_session.flush()
        provider.analyze_review(db_session, review)

    db_session.commit()

    stats = stats_service.get_property_stats(db_session, prop.id)
    assert stats["review_count"] == 2
    assert stats["average_rating"] == 3.0
    assert len(stats["sentiment_breakdown"]) > 0


def test_get_property_stats_raises_for_unknown_property(db_session):
    import pytest

    with pytest.raises(ValueError):
        stats_service.get_property_stats(db_session, "does-not-exist")
