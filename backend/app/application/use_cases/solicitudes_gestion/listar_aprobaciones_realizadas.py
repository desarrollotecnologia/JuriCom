"""Lista las decisiones que tomó un aprobador (aprobó, rechazó, pidió ajustes...)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionHistorialEstado,
)
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion as E,
    normalizar_estado,
)

_ETAPAS_DECISION = (E.SOLICITUD, E.EN_APROBACION, E.APROBACION_ANTICIPO)


@dataclass
class AprobacionRealizada:
    solicitud: SolicitudGestion
    etapa: E
    decision: str
    fecha: Optional[datetime]
    aprobador: str
    comentario: str


def _decision(previa: E, nueva: E) -> str:
    if previa == E.APROBACION_ANTICIPO:
        return "Aprobó anticipo" if nueva == E.GESTION_ANTICIPO else "Rechazó anticipo"
    if nueva == E.CANCELADO:
        return "Rechazó"
    if nueva == E.REVISION:
        return "Pidió ajustes"
    if nueva == E.COTIZACION:
        return "Pidió recotización"
    return "Aprobó (1.ª)" if previa == E.SOLICITUD else "Aprobó (2.ª)"


def decisiones_de_historial(
    historial: list[SolicitudGestionHistorialEstado], creador_id: Optional[int]
) -> list[tuple[SolicitudGestionHistorialEstado, E, str]]:
    """Cada salida de una etapa de aprobación es una decisión de quien la registró.
    Se ignoran los pasos del propio creador (p. ej. consumibles, que saltan la aprobación)."""
    out = []
    for prev, h in zip(historial, historial[1:]):
        previa, nueva = normalizar_estado(prev.etapa), normalizar_estado(h.etapa)
        if previa in _ETAPAS_DECISION and nueva != previa and h.usuario_id and h.usuario_id != creador_id:
            out.append((h, previa, _decision(previa, nueva)))
    return out


class ListarAprobacionesRealizadas:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(self, actor: User) -> list[AprobacionRealizada]:
        if not actor.puede_aprobar_solicitudes_gestion():
            raise UnauthorizedError("No tienes permiso para consultar aprobaciones.")
        # Admin ve las decisiones de todos los aprobadores; el líder solo las suyas.
        usuario_id = None if actor.is_admin() else actor.id
        # ponytail: carga historiales y solicitudes completos; si crece mucho, paginar por fecha.
        historiales = self._solicitudes.historial_de_participante(usuario_id)
        if not historiales:
            return []
        por_id = {s.id: s for s in self._solicitudes.list_all() if s.id in historiales}
        items: list[AprobacionRealizada] = []
        for sid, historial in historiales.items():
            s = por_id.get(sid)
            if s is None:
                continue
            for h, previa, decision in decisiones_de_historial(historial, s.creado_por_id):
                if usuario_id is not None and h.usuario_id != usuario_id:
                    continue
                items.append(
                    AprobacionRealizada(s, previa, decision, h.created_at, h.usuario_username, h.comentario)
                )
        items.sort(key=lambda a: a.fecha or datetime.min, reverse=True)
        return items
