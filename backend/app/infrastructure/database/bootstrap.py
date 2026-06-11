"""Inicialización de la base de datos.

- Crea las tablas si no existen.
- Crea el usuario administrador inicial si no existe.

Se ejecuta automáticamente al arrancar la app.
"""

import logging

from sqlalchemy.exc import OperationalError

from app.domain.value_objects.roles import Role
from app.infrastructure.config import settings
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.session import Base, SessionLocal, engine
from app.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher


logger = logging.getLogger(__name__)


_HINT_PERMISOS = (
    "\n"
    "============================================================\n"
    " No se pudo crear/leer las tablas en la base de datos.\n"
    " Esto suele significar que el usuario MySQL no tiene\n"
    " permisos sobre la base `{db}`.\n"
    "\n"
    " Pídele al DBA que ejecute (como root) el script:\n"
    "     database/grants_setup.sql\n"
    "\n"
    " Que en esencia hace:\n"
    "     CREATE DATABASE IF NOT EXISTS {db}\n"
    "         CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
    "     GRANT ALL PRIVILEGES ON {db}.* TO '{user}'@'%';\n"
    "     FLUSH PRIVILEGES;\n"
    "============================================================"
)


def init_database() -> None:
    """Crea todas las tablas declaradas en los modelos y aplica migraciones."""
    try:
        Base.metadata.create_all(bind=engine)
        from app.infrastructure.database import migrations
        migrations.run_all()
    except OperationalError as e:
        msg = str(e.orig) if e.orig else str(e)
        if "Access denied" in msg or "1044" in msg or "1045" in msg:
            logger.error(_HINT_PERMISOS.format(db=settings.DB_NAME, user=settings.DB_USER))
        raise
    logger.info("Tablas verificadas/creadas en la base de datos.")


def seed_admin_user() -> None:
    """Crea el administrador inicial si no existe."""
    hasher = BcryptPasswordHasher()
    db = SessionLocal()
    try:
        existing = (
            db.query(UserModel)
            .filter(UserModel.username == settings.ADMIN_USERNAME)
            .one_or_none()
        )
        if existing is not None:
            return

        admin = UserModel(
            username=settings.ADMIN_USERNAME,
            password_hash=hasher.hash(settings.ADMIN_PASSWORD),
            role=Role.ADMIN.value,
            is_active=True,
            created_by_id=None,
        )
        db.add(admin)
        db.commit()
        logger.info("Administrador inicial creado: %s", settings.ADMIN_USERNAME)
    finally:
        db.close()
