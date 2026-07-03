"""Registra la recepción física de ítems y avanza a Recepción de Insumos."""

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
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    es_estado_recepcion_abierta,
    normalizar_estado,
)

logger = logging.getLogger(__name__)


class RegistrarRecepcionInsumosSolicitud:
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
        productos_recepcion: dict[int, Decimal],
        observacion: str = "",
        observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> tuple[SolicitudGestion, bool, list[str]]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar recepciones.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen

        if es_flujo_salidas_almacen(solicitud.tipo):
            raise ValueError(
                "Las salidas de almacén no requieren recepción física; "
                "registra la entrega directamente."
            )

        if not es_estado_recepcion_abierta(solicitud.estado):
            raise ValueError(
                "Sólo se puede registrar recepción en Ítems en camino, "
                "Recepción de Insumos o Entrega parcial realizada."
            )

        if not solicitud.tiene_tramite_oc_registrado:
            raise ValueError("Debes registrar el trámite OC antes de la recepción.")

        if not solicitud.actor_puede_gestionar(actor.id, is_admin=actor.is_admin()):
            raise UnauthorizedError("Sólo el gestor asignado puede registrar la recepción.")

        productos_por_id = {
            p.id: p for p in solicitud.productos if p.id is not None
        }
        nuevas_cantidades: dict[int, Decimal] = {}
        lineas: list[str] = []

        for producto_id, cantidad_raw in productos_recepcion.items():
            cantidad_a_recibir = Decimal(str(cantidad_raw))
            if cantidad_a_recibir <= 0:
                continue

            producto = productos_por_id.get(int(producto_id))
            if producto is None:
                raise ValueError(f"No existe el ítem {producto_id} en esta solicitud.")

            if producto.estado_aprobacion == EstadoAprobacionProducto.NO_APROBADO:
                raise ValueError(
                    f"El ítem «{producto.descripcion}» no está aprobado y no puede recibirse."
                )

            pendiente = producto.cantidad_pendiente_recepcion
            if cantidad_a_recibir > pendiente:
                raise ValueError(
                    f"La cantidad recibida de «{producto.descripcion}» supera lo pendiente "
                    f"({pendiente})."
                )

            total_recibido = producto.cantidad_recibida + cantidad_a_recibir
            nuevas_cantidades[producto.id] = total_recibido
            lineas.append(
                producto.linea_historial_recepcion(cantidad_a_recibir, total_recibido)
            )

        if not nuevas_cantidades:
            raise ValueError(
                "Selecciona al menos un ítem e indica la cantidad recibida."
            )

        self._solicitudes.update_productos_cantidad_recibida(
            solicitud_id, nuevas_cantidades
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

        estado_actual = normalizar_estado(solicitud.estado)
        if estado_actual != EstadoSolicitudGestion.RECEPCION_INSUMOS:
            solicitud.estado = EstadoSolicitudGestion.RECEPCION_INSUMOS
            self._solicitudes.update(solicitud)
            comentario = "Recepción de insumos — " + "; ".join(lineas)
            self._solicitudes.registrar_historial(
                solicitud_id,
                EstadoSolicitudGestion.RECEPCION_INSUMOS,
                usuario_id=actor.id,
                comentario=comentario,
            )
        else:
            comentario = "Recepción adicional — " + "; ".join(lineas)
            self._solicitudes.registrar_historial(
                solicitud_id,
                EstadoSolicitudGestion.RECEPCION_INSUMOS,
                usuario_id=actor.id,
                comentario=comentario,
            )

        actualizada = self._solicitudes.get_by_id(solicitud_id)
        if actualizada is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")

        email_enviado = self._notificador.notificar_recepcion_insumos(
            actualizada, actor, lineas
        )
        return (actualizada, email_enviado, lineas)
