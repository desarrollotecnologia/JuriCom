"""Schemas Pydantic para el buzón de pendientes."""

from pydantic import BaseModel


class ModuloPendienteItem(BaseModel):
    titulo: str
    descripcion: str
    cantidad: int
    alta_prioridad: int
    accion_url: str


class BuzonResponse(BaseModel):
    total: int
    alta_prioridad: int
    modulos: list[ModuloPendienteItem]
