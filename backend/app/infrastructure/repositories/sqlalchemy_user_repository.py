"""Implementación de UserRepository sobre SQLAlchemy + MySQL."""

from typing import Optional

from sqlalchemy.orm import Session

from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.value_objects.roles import Role
from app.infrastructure.database.models import UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _parse_extra_roles(valor: str, principal: Role) -> list[Role]:
        """`"juridica,compras"` -> [Role...] sin duplicar el principal ni inválidos."""
        extras: list[Role] = []
        for parte in (valor or "").split(","):
            parte = parte.strip()
            if not parte:
                continue
            try:
                r = Role(parte)
            except ValueError:
                continue
            if r != principal and r not in extras:
                extras.append(r)
        return extras

    @staticmethod
    def _serialize_extra_roles(user: User) -> str:
        return ",".join(r.value for r in user.roles()[1:])

    @classmethod
    def _to_entity(cls, model: UserModel) -> User:
        principal = Role(model.role)
        extras = cls._parse_extra_roles(getattr(model, "extra_roles", "") or "", principal)
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=principal,
            extra_roles=extras,
            nombre=getattr(model, "nombre", "") or "",
            email=getattr(model, "email", "") or "",
            lider_catalog_id=getattr(model, "lider_catalog_id", "") or "",
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by_id=model.created_by_id,
        )

    def get_by_id(self, user_id: int) -> Optional[User]:
        model = self._db.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    def get_by_username(self, username: str) -> Optional[User]:
        model = (
            self._db.query(UserModel)
            .filter(UserModel.username == username)
            .one_or_none()
        )
        return self._to_entity(model) if model else None

    def list_all(self) -> list[User]:
        models = self._db.query(UserModel).order_by(UserModel.id.asc()).all()
        return [self._to_entity(m) for m in models]

    def create(self, user: User) -> User:
        model = UserModel(
            username=user.username,
            password_hash=user.password_hash,
            role=user.role.value,
            extra_roles=self._serialize_extra_roles(user),
            nombre=(user.nombre or "").strip(),
            email=(user.email or "").strip(),
            lider_catalog_id=(user.lider_catalog_id or "").strip(),
            is_active=user.is_active,
            created_by_id=user.created_by_id,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def update(self, user: User) -> User:
        if user.id is None:
            raise ValueError("No se puede actualizar un usuario sin id.")
        model = self._db.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User {user.id} no existe en BD.")

        model.username = user.username
        model.password_hash = user.password_hash
        model.role = user.role.value
        model.extra_roles = self._serialize_extra_roles(user)
        model.nombre = (user.nombre or "").strip()
        model.email = (user.email or "").strip()
        model.lider_catalog_id = (user.lider_catalog_id or "").strip()
        model.is_active = user.is_active

        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def delete(self, user_id: int) -> None:
        model = self._db.get(UserModel, user_id)
        if model is None:
            return
        self._db.delete(model)
        self._db.commit()
