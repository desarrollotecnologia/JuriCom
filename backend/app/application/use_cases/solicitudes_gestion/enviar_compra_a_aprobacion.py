"""Compras devuelve una compra directa al flujo de aprobación del líder de área."""

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


# Estados desde los que Compras puede devolver una compra directa a aprobación.
_ETAPAS_ENVIABLES = (
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.COTIZACION,
)


class EnviarCompraAAprobacion:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._notificador = notificador

    def execute(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden enviar una compra a aprobación."
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not bool(getattr(solicitud, "directa_compras", False)):
            raise ValueError(
                "Sólo las compras directas pueden enviarse a aprobación del líder."
            )

        estado = normalizar_estado(solicitud.estado)
        if estado not in _ETAPAS_ENVIABLES:
            raise ValueError(
                "La compra ya no está en una etapa que permita enviarla a aprobación."
            )

        # Vuelve al inicio del flujo normal: pendiente de aprobación del líder de área.
        ids = {p.id for p in solicitud.productos if p.id is not None}
        if ids:
            self._solicitudes.update_productos_estado_aprobacion(
                solicitud.id,
                {pid: EstadoAprobacionProducto.PENDIENTE.value for pid in ids},
            )

        solicitud.estado = EstadoSolicitudGestion.SOLICITUD
        solicitud.directa_compras = False
        solicitud.gestor_id = None
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.SOLICITUD,
            usuario_id=actor.id,
            comentario=f"Enviada a aprobación del líder por {actor.username}",
        )
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        resultado = refreshed or actualizada
        if self._notificador:
            self._notificador.notificar_compra_enviada_a_aprobacion(resultado, actor)
        return resultado
