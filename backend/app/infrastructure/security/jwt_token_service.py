"""Implementación de TokenService con JWT (python-jose)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.application.interfaces.token_service import TokenService
from app.infrastructure.config import settings


class JwtTokenService(TokenService):
    def __init__(
        self,
        secret_key: str = settings.SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
        expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    ) -> None:
        self._secret = secret_key
        self._algo = algorithm
        self._expire = expire_minutes

    def create_access_token(self, subject: str, extra_claims: Optional[dict] = None) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._expire)).timestamp()),
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, self._secret, algorithm=self._algo)

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algo])
        except JWTError as e:
            raise ValueError(f"Token inválido: {e}") from e
