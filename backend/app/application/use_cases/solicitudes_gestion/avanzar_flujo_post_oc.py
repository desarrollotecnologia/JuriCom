"""Avanza el flujo tras registrar la OC: Tramitada OC (historial) → Ítems en camino."""

from app.application.interfaces.solicitud_gestion_repository import SolicitudGestionRepository
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion


def avanzar_a_items_en_camino(
    repo: SolicitudGestionRepository,
    solicitud_id: int,
    actor_id: int,
    *,
    comentario_tramitada: str,
) -> SolicitudGestion | None:
    repo.registrar_historial(
        solicitud_id,
        EstadoSolicitudGestion.TRAMITADA_OC,
        usuario_id=actor_id,
        comentario=comentario_tramitada,
    )

    solicitud = repo.get_by_id(solicitud_id)
    if solicitud is None:
        return None

    solicitud.estado = EstadoSolicitudGestion.ITEMS_EN_CAMINO
    repo.update(solicitud)
    repo.registrar_historial(
        solicitud_id,
        EstadoSolicitudGestion.ITEMS_EN_CAMINO,
        usuario_id=actor_id,
        comentario="Ítems en camino — en espera de recepción física en Compras",
    )
    return repo.get_by_id(solicitud_id)
