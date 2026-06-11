"""Configuración pública para el frontend."""

from fastapi import APIRouter, Depends

from app.domain.entities.user import User
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import get_current_user


router = APIRouter(prefix="/config", tags=["config"])


@router.get("/aprobacion-emails")
def aprobacion_emails(_: User = Depends(get_current_user)) -> dict:
    """Correos vinculados al flujo de aprobación líder inmediato → gerencia."""
    return {
        "lider_inmediato": settings.LIDER_INMEDIATO_EMAIL.strip(),
        "gerencia": settings.GERENCIA_EMAIL.strip(),
        "app_url": settings.public_url,
    }
