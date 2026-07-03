"""Marca una solicitud como entregada (cierre del flujo) y notifica al solicitante."""

import logging
from decimal import Decimal

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    es_estado_entrega_abierta,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen

logger = logging.getLogger(__name__)


class MarcarEntregaSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        notificador: NotificadorSolicitudGestion,
        storage: FileStorage,
    ) -> None:
        self._solicitudes = solicitudes
        self._notificador = notificador
        self._storage = storage

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> tuple[SolicitudGestion, bool]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar la entrega.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_estado_entrega_abierta(solicitud.estado):
            raise ValueError(
                "La solicitud debe estar en Recepción de Insumos o Entrega parcial realizada."
            )

        es_salidas = solicitud.es_salidas_almacen

        if not es_salidas and not solicitud.tiene_tramite_oc_registrado:
            raise ValueError(
                "Debes registrar el trámite OC antes de marcar la entrega."
            )

        if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
            raise UnauthorizedError("Sólo el gestor asignado puede registrar la entrega.")

        productos_entrega = solicitud.productos_para_entrega
        if not productos_entrega:
            raise ValueError("No hay ítems aprobados para entregar.")

        if not es_salidas:
            pendientes_recepcion = [
                p for p in productos_entrega if p.cantidad_pendiente_recepcion > 0
            ]
            if pendientes_recepcion:
                nombres = ", ".join(f"«{p.descripcion}»" for p in pendientes_recepcion)
                raise ValueError(
                    f"Aún hay ítems sin recepción física completa: {nombres}. "
                    "Registra la llegada o usa entrega parcial de lo recibido."
                )

        pendientes_entrega = [
            p
            for p in productos_entrega
            if (
                (p.cantidad - p.cantidad_entregada)
                if es_salidas
                else p.cantidad_disponible_entrega
            )
            <= 0
        ]
        if len(pendientes_entrega) == len(productos_entrega):
            raise ValueError(
                "No hay cantidades pendientes de entrega al solicitante."
            )

        cantidades_finales: dict[int, Decimal] = {}
        for producto in productos_entrega:
            if producto.id is None:
                continue
            if es_salidas:
                pendiente = producto.cantidad - producto.cantidad_entregada
                if pendiente <= 0:
                    continue
                cantidades_finales[producto.id] = producto.cantidad_entregada + pendiente
            else:
                if producto.cantidad_disponible_entrega <= 0:
                    continue
                cantidades_finales[producto.id] = producto.cantidad_entregada + (
                    producto.cantidad_disponible_entrega
                )

        if cantidades_finales:
            self._solicitudes.update_productos_cantidad_entregada(
                solicitud_id, cantidades_finales
            )

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or adjuntos_obs:
            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="gestor",
                archivos=adjuntos_obs,
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")

        solicitud.estado = EstadoSolicitudGestion.ENTREGADO
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.ENTREGADO,
            usuario_id=actor.id,
            comentario=f"Entrega total registrada por {actor.username}",
        )

        email_enviado = self._notificador.notificar_entrega(
            actualizada, actor, EstadoSolicitudGestion.ENTREGADO
        )

        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return (refreshed or actualizada, email_enviado)
