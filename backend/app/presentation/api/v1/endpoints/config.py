"""Configuración pública para el frontend."""

from fastapi import APIRouter, Depends

from app.domain.entities.user import User
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import get_current_user


router = APIRouter(prefix="/config", tags=["config"])


@router.get("/aprobacion-emails")
def aprobacion_emails(_: User = Depends(get_current_user)) -> dict:
    """Correos y reglas del flujo de aprobación líder → gerencia."""
    return {
        "lider_inmediato": settings.LIDER_INMEDIATO_EMAIL.strip(),
        "gerencia": settings.GERENCIA_EMAIL.strip(),
        "umbral_cop": float(settings.aprobacion_umbral_cop),
        "diego_serrano": settings.APROBACION_DIEGO_SERRANO_EMAIL.strip(),
        "gerencia_general": (
            settings.APROBACION_GERENCIA_GENERAL_EMAIL.strip()
            or settings.GERENCIA_EMAIL.strip()
        ),
        "app_url": settings.public_url,
    }
