"""
Livello di accesso al database: engine SQLAlchemy, sessione e base dichiarativa.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency FastAPI: fornisce una sessione DB per request e la chiude sempre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea le tabelle se non esistono. In produzione si userebbero migration
    Alembic; qui l'approccio e' volutamente semplice per l'avvio via Docker."""
    from app import models  # noqa: F401  (assicura la registrazione dei model)

    Base.metadata.create_all(bind=engine)
