"""Dependencias compartidas de FastAPI (DI).

Sigue el principio de inversión de dependencias: aquí ensamblamos las
implementaciones concretas y se las pasamos a los casos de uso.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import EmailNotifier
from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.token_service import TokenService
from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.infrastructure.database.session import get_db
from app.infrastructure.email import SmtpEmailNotifier
from app.infrastructure.repositories import (
    SqlAlchemyContratoRepository,
    SqlAlchemyUserRepository,
)
from app.infrastructure.security import BcryptPasswordHasher, JwtTokenService
from app.infrastructure.storage import LocalFileStorage


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_contrato_repository(db: Session = Depends(get_db)) -> ContratoRepository:
    return SqlAlchemyContratoRepository(db)


def get_password_hasher() -> PasswordHasher:
    return BcryptPasswordHasher()


def get_token_service() -> TokenService:
    return JwtTokenService()


def get_file_storage() -> FileStorage:
    return LocalFileStorage()


def get_email_notifier() -> EmailNotifier:
    return SmtpEmailNotifier()


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    tokens: TokenService = Depends(get_token_service),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = tokens.decode_token(token)
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = users.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo.",
        )
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    if not current.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador.",
        )
    return current
