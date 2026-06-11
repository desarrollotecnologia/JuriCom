"""Endpoint para descargar archivos adjuntos a un contrato."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.use_cases.contratos import GetContrato
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
)


router = APIRouter(prefix="/archivos", tags=["archivos"])


@router.get("/{contrato_id}/{archivo_id}")
def descargar_archivo(
    contrato_id: int,
    archivo_id: int,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
):
    try:
        contrato = GetContrato(contratos).execute(actor=current, contrato_id=contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    archivo = next((a for a in contrato.archivos if a.id == archivo_id), None)
    if archivo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado."
        )

    ruta_completa: Path = settings.upload_dir_path / archivo.ruta_almacenamiento
    if not ruta_completa.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="El archivo ya no está disponible en disco.",
        )

    return FileResponse(
        path=str(ruta_completa),
        media_type=archivo.mime_type,
        filename=archivo.nombre_original,
        content_disposition_type="attachment",
    )
