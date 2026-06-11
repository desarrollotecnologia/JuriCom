"""Caso de uso: iniciar sesión."""

from dataclasses import dataclass

from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.token_service import TokenService
from app.application.interfaces.user_repository import UserRepository
from app.domain.entities.user import User
from app.domain.exceptions import InvalidCredentialsError


@dataclass
class LoginResult:
    access_token: str
    token_type: str
    user: User


class LoginUser:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    def execute(self, username: str, password: str) -> LoginResult:
        user = self._users.get_by_username(username)
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Usuario o contraseña incorrectos.")

        if not self._hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Usuario o contraseña incorrectos.")

        token = self._tokens.create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role.value, "username": user.username},
        )
        return LoginResult(access_token=token, token_type="bearer", user=user)
