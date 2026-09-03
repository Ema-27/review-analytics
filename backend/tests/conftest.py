"""
Configurazione condivisa dei test.

I test usano:
  * SQLite in-memory al posto di PostgreSQL, per essere veloci e non
    richiedere un database esterno durante lo sviluppo/CI;
  * il MockAIProvider (AI_PROVIDER=mock) al posto dei modelli Hugging Face
    reali, per non dipendere dal download di modelli multi-GB e per avere
    esecuzioni deterministiche e istantanee.

Questo e' possibile perche' l'applicazione e' stata progettata con un layer
di persistenza basato su tipi SQLAlchemy portabili (JSON generico anziche'
JSONB specifico di Postgres) e con un provider AI dietro un'interfaccia
astratta sostituibile (vedi app/ai_providers/base.py).
"""
from __future__ import annotations

import os

os.environ["AI_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
