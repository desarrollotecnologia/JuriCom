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
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            password_hash=model.password_hash,
            role=Role(model.role),
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
