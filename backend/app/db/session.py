"""Database engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_options: dict[str, object] = {"connect_args": connect_args, "pool_pre_ping": True}
if not settings.database_url.startswith("sqlite"):
    engine_options["pool_recycle"] = 240
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
