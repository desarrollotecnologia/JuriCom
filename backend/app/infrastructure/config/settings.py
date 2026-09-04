"""Configuración global cargada desde .env."""

import socket
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]


def _detect_lan_ip() -> str | None:
    """IP de la red local (para enlaces en correos cuando .env dice localhost)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "Juridica"
    DB_ACTIVATE_ROLE: str = ""

    SECRET_KEY: str = Field(..., min_length=16)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    ADMIN_USERNAME: str = "gerencia2026*"
    ADMIN_PASSWORD: str = "gerencia2026*"

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"
    APP_PUBLIC_URL: str = "http://localhost:8000"

    UPLOAD_DIR: str = "../uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

    # --- SMTP ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USE_SSL: bool = True
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "JURICOM"

    # Modo prueba: si tiene un correo, TODOS los envíos se redirigen ahí.
    # Dejar vacío para volver a la normalidad.
    EMAIL_OVERRIDE_TO: str = ""

    JURIDICA_EMAILS: str = ""
    COMPRAS_EMAILS: str = ""

    # Correos del flujo de aprobación líder → gerencia (radicar / otrosí).
    # Ver .env: APROBACION_UMBRAL_COP, APROBACION_DIEGO_SERRANO_EMAIL,
    # APROBACION_GERENCIA_GENERAL_EMAIL.
    LIDER_INMEDIATO_EMAIL: str = "coordinacion.juridica@colbeef.com"
    GERENCIA_EMAIL: str = "tommyelite25@gmail.com"
    APROBACION_UMBRAL_COP: str = "10000000"
    APROBACION_DIEGO_SERRANO_EMAIL: str = "gerencia.financiera@colbeef.com"
    APROBACION_GERENCIA_GENERAL_EMAIL: str = "gerencia.general@colbeef.com"

    # Umbral para el acta de liquidación: contratos con valor MAYOR a este monto
    # exigen que Jurídica elabore/cargue el acta (además del informe final del
    # supervisor). Los de valor igual o menor solo requieren el informe final.
    LIQUIDACION_ACTA_UMBRAL_COP: str = "15000000"

    @property
    def aprobacion_umbral_cop(self) -> Decimal:
        return Decimal(str(self.APROBACION_UMBRAL_COP).replace("_", "").strip() or "10000000")

    @property
    def liquidacion_acta_umbral_cop(self) -> Decimal:
        return Decimal(
            str(self.LIQUIDACION_ACTA_UMBRAL_COP).replace("_", "").strip() or "15000000"
        )

    @property
    def juridica_emails_list(self) -> list[str]:
        return [e.strip() for e in self.JURIDICA_EMAILS.split(",") if e.strip()]

    @property
    def compras_emails_list(self) -> list[str]:
        return [e.strip() for e in self.COMPRAS_EMAILS.split(",") if e.strip()]

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USERNAME and self.SMTP_FROM_EMAIL)

    @property
    def public_url(self) -> str:
        """URL base para enlaces en correos y red local (no localhost si hay LAN)."""
        configured = self.APP_PUBLIC_URL.rstrip("/")
        host = (urlparse(configured).hostname or "").lower()
        if host not in ("localhost", "127.0.0.1"):
            return configured
        lan = _detect_lan_ip()
        if lan:
            return f"http://{lan}:{self.APP_PORT}"
        return configured

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def upload_dir_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        if not path.is_absolute():
            path = (BASE_DIR / path).resolve()
        return path

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
