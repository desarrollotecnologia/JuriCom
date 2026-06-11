"""Configuración de SQLAlchemy (engine + session)."""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.infrastructure.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)


if settings.DB_ACTIVATE_ROLE:
    # MySQL 8: si el usuario tiene permisos via rol, lo activamos al conectar.
    @event.listens_for(engine, "connect")
    def _activate_role(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute(f"SET ROLE `{settings.DB_ACTIVATE_ROLE}`")
        finally:
            cursor.close()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI: abre una sesión por request y la cierra."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
