"""
Test end-to-end (con TestClient FastAPI + SQLite in-memory + MockAIProvider)
che verificano l'intera catena: seeding del dataset dimostrativo -> analisi
NLP automatica -> endpoint di consultazione strutture/recensioni -> endpoint
di analytics (trend, sentiment, aspetti) -> endpoint di AI generativa
(sintesi, confronto, suggerimenti).
"""
from __future__ import annotations

import json
from pathlib import Path


def test_seed_demo_dataset_populates_properties_and_reviews(client):
    resp = client.post("/api/v1/ingestion/seed-demo-data")
    assert resp.status_code == 200
    body = resp.json()
    assert body["properties"] > 0
    assert body["reviews"] > 0


def test_list_properties_after_seed(client):
    client.post("/api/v1/ingestion/seed-demo-data")
    resp = client.get("/api/v1/properties")
    assert resp.status_code == 200
    props = resp.json()
    assert len(props) > 0
    assert all("average_rating" in p for p in props)


def test_analytics_endpoint_returns_trend_and_aspects(client):
    client.post("/api/v1/ingestion/seed-demo-data")
    props = client.get("/api/v1/properties").json()
    property_id = props[0]["id"]

    resp = client.get(f"/api/v1/analytics/properties/{property_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["review_count"] > 0
    assert isinstance(data["rating_trend"], list)
    assert isinstance(data["top_aspects"], list)


def test_ai_summary_generation(client):
    client.post("/api/v1/ingestion/seed-demo-data")
    props = client.get("/api/v1/properties").json()
    property_id = props[0]["id"]

    resp = client.post("/api/v1/ai/summary", json={"property_id": property_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "summary"
    assert len(data["content"]) > 20


def test_ai_comparison_generation(client):
    client.post("/api/v1/ingestion/seed-demo-data")
    props = client.get("/api/v1/properties").json()
    hotel_ids = [p["id"] for p in props if p["type"] == "hotel"][:2]
    assert len(hotel_ids) == 2

    resp = client.post("/api/v1/ai/comparison", json={"property_ids": hotel_ids})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "competitive_comparison"
    assert len(data["content"]) > 20


def test_ai_suggestions_generation(client):
    client.post("/api/v1/ingestion/seed-demo-data")
    props = client.get("/api/v1/properties").json()
    property_id = props[0]["id"]

    resp = client.post("/api/v1/ai/suggestions", json={"property_id": property_id})
    assert resp.status_code == 200
    assert len(resp.json()["content"]) > 20


def test_generated_reports_are_persisted_and_filterable(client):
    client.post("/api/v1/ingestion/seed-demo-data")
    props = client.get("/api/v1/properties").json()
    pid = props[0]["id"]

    client.post("/api/v1/ai/summary", json={"property_id": pid})

    all_reports = client.get("/api/v1/ai/reports").json()
    assert any(r["report_type"] == "summary" and pid in r["property_ids"] for r in all_reports)

    filtered = client.get(
        "/api/v1/ai/reports", params={"property_id": pid, "report_type": "summary", "limit": 1}
    ).json()
    assert len(filtered) == 1
    assert filtered[0]["report_type"] == "summary"
    assert pid in filtered[0]["property_ids"]

    other = client.get(
        "/api/v1/ai/reports", params={"property_id": props[1]["id"], "report_type": "summary"}
    ).json()
    assert other == []


def test_ingestion_run_unknown_property_without_apify_ingests_nothing(client):
    """Senza Apify e senza corrispondenza nel dataset di esempio, la ingestion
    NON deve inventare dati (in passato ricadeva sulle recensioni di un'altra
    struttura, rendendo identiche strutture diverse)."""
    resp = client.post(
        "/api/v1/ingestion/run",
        json={
            "property_name": "Hotel Che Non Esiste XYZ",
            "property_type": "hotel",
            "city": "Torino",
            "country": "Italia",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["records_ingested"] == 0
    assert body["error_message"]
    # la struttura vuota non viene creata
    assert client.get("/api/v1/properties", params={"city": "Torino"}).json() == []


def test_ingestion_run_matching_sample_name_ingests_reviews(client):
    dataset_path = Path(__file__).resolve().parent.parent / "app" / "data" / "sample_reviews.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    entry = dataset[0]
    resp = client.post(
        "/api/v1/ingestion/run",
        json={
            "property_name": entry["name"],
            "property_type": entry["type"],
            "city": entry["city"],
            "country": entry["country"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["records_ingested"] > 0
    assert body["source"] == "sample_dataset"


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
