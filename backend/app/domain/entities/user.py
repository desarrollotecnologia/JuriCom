"""Entidad User (capa de dominio, pura).

Las entidades de dominio NO conocen ni a SQLAlchemy ni a FastAPI.
Son objetos planos con reglas de negocio.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.value_objects.roles import Role


@dataclass
class User:
    username: str
    password_hash: str
    role: Role
    id: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_juridica(self) -> bool:
        return self.role == Role.JURIDICA

    def is_compras(self) -> bool:
        return self.role == Role.COMPRAS

    def can_manage_users(self) -> bool:
        """Sólo el administrador puede gestionar usuarios."""
        return self.is_admin()
