"""Toma una solicitud en el panel y avanza el flujo según el tipo."""

from decimal import Decimal

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen


class GestionarSolicitudPanel:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden gestionar solicitudes.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        estado = normalizar_estado(solicitud.estado)
        es_salidas = es_flujo_salidas_almacen(solicitud.tipo)

        if es_salidas:
            return self._gestionar_salidas_almacen(actor, solicitud_id, solicitud, estado)

        if estado == EstadoSolicitudGestion.COTIZACION:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado == EstadoSolicitudGestion.GESTIONANDO_SERVICIO:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado == EstadoSolicitudGestion.TRAMITANDO_OC:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado == EstadoSolicitudGestion.ENTREGADO_PARCIAL:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            return solicitud

        if estado == EstadoSolicitudGestion.ITEMS_EN_CAMINO:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado == EstadoSolicitudGestion.RECEPCION_INSUMOS:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            return solicitud

        if estado == EstadoSolicitudGestion.TRAMITADA_OC:
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado != EstadoSolicitudGestion.PRIMERA_APROBACION:
            raise ValueError(
                "Sólo se pueden gestionar solicitudes en Primera Aprobación, Cotización, "
                "Gestionando servicio, Tramitando OC, Ítems en camino, Recepción de Insumos, "
                "Tramitada OC o Entrega parcial realizada."
            )

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Esta solicitud ya fue tomada por otro gestor.")

        solicitud.gestor_id = actor.id
        solicitud.estado = EstadoSolicitudGestion.COTIZACION
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.COTIZACION,
            usuario_id=actor.id,
            comentario=f"Gestión iniciada por {actor.username}",
        )
        return actualizada

    def _gestionar_salidas_almacen(
        self,
        actor: User,
        solicitud_id: int,
        solicitud: SolicitudGestion,
        estado: EstadoSolicitudGestion,
    ) -> SolicitudGestion:
        if estado in (
            EstadoSolicitudGestion.RECEPCION_INSUMOS,
            EstadoSolicitudGestion.ENTREGADO_PARCIAL,
        ):
            if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
                raise UnauthorizedError("Esta solicitud está siendo gestionada por otro usuario.")
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
                return self._solicitudes.update(solicitud)
            return solicitud

        if estado not in (
            EstadoSolicitudGestion.PRIMERA_APROBACION,
            EstadoSolicitudGestion.COTIZACION,
        ):
            raise ValueError(
                "Las salidas de almacén sólo se gestionan tras la aprobación del líder "
                "o durante la entrega de productos."
            )

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Esta solicitud ya fue tomada por otro gestor.")

        return self._activar_entrega_salidas_almacen(actor, solicitud_id, solicitud)

    def _activar_entrega_salidas_almacen(
        self,
        actor: User,
        solicitud_id: int,
        solicitud: SolicitudGestion,
    ) -> SolicitudGestion:
        solicitud.gestor_id = actor.id
        cantidades: dict[int, Decimal] = {
            p.id: p.cantidad
            for p in solicitud.productos_para_entrega
            if p.id is not None
        }
        if cantidades:
            self._solicitudes.update_productos_cantidad_recibida(solicitud_id, cantidades)

        solicitud.estado = EstadoSolicitudGestion.RECEPCION_INSUMOS
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.RECEPCION_INSUMOS,
            usuario_id=actor.id,
            comentario=f"Gestión de entrega de almacén iniciada por {actor.username}",
        )
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return refreshed or actualizada
