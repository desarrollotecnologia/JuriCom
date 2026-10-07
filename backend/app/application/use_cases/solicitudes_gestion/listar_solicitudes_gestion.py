"""Lista solicitudes del módulo Gestión de Solicitudes."""

from typing import Optional

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.supervisiones_solicitudes import (
    emails_supervisados,
    es_miembro_comite_tecnico,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


def _en_comite_tecnico(s: SolicitudGestion) -> bool:
    return bool(s.requiere_comite_tecnico) and (
        normalizar_estado(s.estado) == EstadoSolicitudGestion.COMITE
    )


class ListarSolicitudesGestion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        *,
        tipo: Optional[TipoSolicitudGestion] = None,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        if not actor.puede_crear_solicitudes_gestion():
            raise UnauthorizedError("No tienes permiso para consultar solicitudes.")

        creador_id: Optional[int] = None
        if actor.ve_solo_propias_solicitudes_gestion():
            creador_id = actor.id

        supervisados = emails_supervisados(actor.email)
        comite = es_miembro_comite_tecnico(actor.email)
        if creador_id is not None and (supervisados or comite):
            # Ve las propias + las de los solicitantes que supervisa (por correo)
            # + las SRV en mesa técnica si integra el comité técnico.
            permitidos = supervisados | {(actor.email or "").strip().lower()}
            todas = self._solicitudes.list_all(tipo=tipo, query=query)
            return [
                s
                for s in todas
                if s.creado_por_id == actor.id
                or (s.creado_por_email or "").strip().lower() in permitidos
                or (comite and _en_comite_tecnico(s))
            ]

        return self._solicitudes.list_all(
            creador_id=creador_id,
            tipo=tipo,
            query=query,
        )
