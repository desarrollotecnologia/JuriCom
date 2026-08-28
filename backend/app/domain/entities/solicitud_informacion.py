"""Entidad SolicitudInformacion (capa de dominio, pura).

Representa una solicitud de información faltante que Jurídica le hace a Compras
sobre un contrato. Compras tiene un plazo (días hábiles) para responder.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from app.domain.entities.contrato import (
    ArchivoAdjunto,
    contar_dias_habiles,
    sumar_dias_habiles,
)

# Días hábiles que tiene Compras para responder por defecto.
DIAS_RESPUESTA_DEFAULT = 2

ESTADO_PENDIENTE = "pendiente"
ESTADO_RESPONDIDA = "respondida"


def calcular_fecha_limite_respuesta(
    desde: date, dias: int = DIAS_RESPUESTA_DEFAULT
) -> date:
    """Fecha tope para responder, contada en días hábiles desde el día
    siguiente a `desde`."""
    return sumar_dias_habiles(desde, dias)


@dataclass
class SolicitudInformacion:
    contrato_id: int
    solicitado_por_id: int
    mensaje: str
    id: Optional[int] = None
    solicitado_por_username: str = ""
    fecha_limite_respuesta: Optional[date] = None
    estado: str = ESTADO_PENDIENTE
    respuesta: str = ""
    respondido_por_id: Optional[int] = None
    respondido_por_username: str = ""
    respondido_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    archivos: list[ArchivoAdjunto] = field(default_factory=list)

    @property
    def pendiente(self) -> bool:
        return self.estado == ESTADO_PENDIENTE

    def dias_para_responder(self, hoy: Optional[date] = None) -> Optional[int]:
        """Días hábiles que faltan para el vencimiento (negativo si ya pasó)."""
        if not self.fecha_limite_respuesta or not self.pendiente:
            return None
        return contar_dias_habiles(hoy or date.today(), self.fecha_limite_respuesta)

    def vencida(self, hoy: Optional[date] = None) -> bool:
        dias = self.dias_para_responder(hoy)
        return dias is not None and dias < 0
