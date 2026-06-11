"""Endpoints del buzón de pendientes."""

from fastapi import APIRouter, Depends

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.use_cases.tareas import ObtenerBuzon
from app.domain.entities.user import User
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
)
from app.presentation.api.v1.schemas.tarea_schemas import BuzonResponse, ModuloPendienteItem


router = APIRouter(prefix="/tareas", tags=["tareas"])


def _to_response(buzon) -> BuzonResponse:
    return BuzonResponse(
        total=buzon.total,
        alta_prioridad=buzon.alta_prioridad,
        modulos=[
            ModuloPendienteItem(
                titulo=m.titulo,
                descripcion=m.descripcion,
                cantidad=m.cantidad,
                alta_prioridad=m.alta_prioridad,
                accion_url=m.accion_url,
            )
            for m in buzon.modulos
        ],
    )


@router.get("/buzon", response_model=BuzonResponse)
def obtener_buzon(
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> BuzonResponse:
    return _to_response(ObtenerBuzon(contratos).execute(actor=current))


@router.get("/bandeja", response_model=BuzonResponse, include_in_schema=False)
def obtener_bandeja_legacy(
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> BuzonResponse:
    """Alias legacy — usar /buzon."""
    return _to_response(ObtenerBuzon(contratos).execute(actor=current))
