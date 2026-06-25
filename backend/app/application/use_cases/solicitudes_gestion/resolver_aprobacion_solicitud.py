"""Aprueba o cancela una solicitud de compra pendiente."""

from decimal import Decimal

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
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
    es_pendiente_aprobacion,
    normalizar_estado,
    siguiente_etapa,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class ResolverAprobacionSolicitud:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def aprobar(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
        storage: FileStorage | None = None,
        tipo_aprobacion: str = "total",
        productos_aprobados_ids: list[int] | None = None,
        productos_cantidades: dict[int, Decimal] | None = None,
    ) -> SolicitudGestion:
        solicitud = self._get_pendiente(actor, solicitud_id)
        etapa_actual = normalizar_estado(solicitud.estado)

        contexto_rol = (
            "aprobador_primera"
            if etapa_actual == EstadoSolicitudGestion.SOLICITUD
            else "aprobador_segunda"
        )
        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        adjuntos = archivos or []
        if nota_texto or nota_html or adjuntos:
            from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
                AgregarObservacionSolicitud,
            )

            AgregarObservacionSolicitud(self._solicitudes, storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol=contexto_rol,
                archivos=adjuntos,
            )

        comentario_historial = ""
        if etapa_actual == EstadoSolicitudGestion.SOLICITUD:
            self._aplicar_cantidades_productos(solicitud, productos_cantidades)
            comentario_historial = self._aplicar_primera_aprobacion_productos(
                solicitud,
                tipo_aprobacion,
                productos_aprobados_ids,
            )

        if etapa_actual == EstadoSolicitudGestion.EN_APROBACION:
            proxima = EstadoSolicitudGestion.TRAMITANDO_OC
        else:
            proxima = siguiente_etapa(etapa_actual)
        if proxima is None:
            raise ValueError("La solicitud ya completó el flujo de aprobación.")

        solicitud.estado = proxima
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            proxima,
            usuario_id=actor.id,
            comentario=comentario_historial or f"Avance a: {proxima.label}",
        )
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return refreshed or actualizada

    def _aplicar_cantidades_productos(
        self,
        solicitud: SolicitudGestion,
        productos_cantidades: dict[int, Decimal] | None,
    ) -> None:
        if not productos_cantidades:
            return

        ids_validos = {p.id for p in solicitud.productos if p.id is not None}
        cantidades: dict[int, Decimal] = {}
        for pid, cant in productos_cantidades.items():
            if pid not in ids_validos:
                continue
            if cant <= 0:
                raise ValueError("Todas las cantidades deben ser mayores a cero.")
            cantidades[pid] = cant

        if cantidades:
            self._solicitudes.update_productos_cantidades(solicitud.id, cantidades)

    def _aplicar_primera_aprobacion_productos(
        self,
        solicitud: SolicitudGestion,
        tipo_aprobacion: str,
        productos_aprobados_ids: list[int] | None,
    ) -> str:
        if not solicitud.productos:
            return ""

        ids_validos = {p.id for p in solicitud.productos if p.id is not None}
        if not ids_validos:
            return ""

        modo = (tipo_aprobacion or "total").strip().lower()
        aprobados_ids = set(ids_validos)

        if modo == "parcial":
            seleccionados = {
                pid
                for pid in (productos_aprobados_ids or [])
                if pid in ids_validos
            }
            if not seleccionados:
                raise ValueError("Debes seleccionar al menos un ítem para aprobar parcialmente.")
            aprobados_ids = seleccionados

        estados = {
            pid: (
                EstadoAprobacionProducto.APROBADO.value
                if pid in aprobados_ids
                else EstadoAprobacionProducto.NO_APROBADO.value
            )
            for pid in ids_validos
        }
        self._solicitudes.update_productos_estado_aprobacion(solicitud.id, estados)

        total = len(ids_validos)
        aprobados = len(aprobados_ids)
        if aprobados < total:
            return f"Aprobación parcial: {aprobados} de {total} ítems aprobados"
        return f"Aprobación total: {total} ítems aprobados"

    def rechazar(
        self,
        actor: User,
        solicitud_id: int,
        motivo: str = "",
    ) -> SolicitudGestion:
        solicitud = self._get_pendiente(actor, solicitud_id)
        etapa_actual = normalizar_estado(solicitud.estado)
        contexto_rol = (
            "aprobador_primera"
            if etapa_actual == EstadoSolicitudGestion.SOLICITUD
            else "aprobador_segunda"
        )
        solicitud.estado = EstadoSolicitudGestion.CANCELADO
        motivo = (motivo or "").strip()
        if motivo:
            from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
                AgregarObservacionSolicitud,
            )

            AgregarObservacionSolicitud(self._solicitudes).execute(
                actor,
                solicitud_id,
                contenido=f"<p><strong>Cancelación:</strong> {motivo}</p>",
                contenido_texto=f"Cancelación: {motivo}",
                contexto_rol=contexto_rol,
            )

        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.CANCELADO,
            usuario_id=actor.id,
            comentario=motivo or "Solicitud cancelada",
        )
        return actualizada

    def _get_pendiente(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden aprobar o cancelar solicitudes."
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if solicitud.tipo != TipoSolicitudGestion.COMPRA:
            raise ValueError("Sólo se pueden aprobar solicitudes de compra.")

        if not es_pendiente_aprobacion(solicitud.estado):
            raise ValueError("Esta solicitud ya fue procesada o no está en etapa de aprobación.")

        if actor.is_compras() and not actor.is_admin() and solicitud.creado_por_id == actor.id:
            raise UnauthorizedError("No puedes aprobar o cancelar tu propia solicitud.")

        return solicitud
