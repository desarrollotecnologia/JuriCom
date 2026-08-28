"""El solicitante responde los ajustes pedidos y reenvía a primera aprobación."""

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
    normalizar_estado,
)


class ResponderRevisionSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._notificador = notificador

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
        storage: FileStorage | None = None,
        titulo: str | None = None,
        proveedor_sugerido: str | None = None,
        descripcion_servicio: str | None = None,
        descripcion_servicio_texto: str | None = None,
        observaciones: str | None = None,
        observaciones_texto: str | None = None,
        centro_costo_area: str | None = None,
    ) -> SolicitudGestion:
        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        es_creador = solicitud.creado_por_id == actor.id
        if not (actor.is_admin() or es_creador):
            raise UnauthorizedError(
                "Sólo el solicitante que creó la solicitud (o el Administrador) "
                "puede responder los ajustes."
            )

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.REVISION:
            raise ValueError("Esta solicitud no está en revisión.")

        self._aplicar_ajustes_campos(
            solicitud,
            titulo=titulo,
            proveedor_sugerido=proveedor_sugerido,
            descripcion_servicio=descripcion_servicio,
            descripcion_servicio_texto=descripcion_servicio_texto,
            observaciones=observaciones,
            observaciones_texto=observaciones_texto,
            centro_costo_area=centro_costo_area,
        )

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        if not nota_texto and not nota_html:
            raise ValueError("Describe los ajustes realizados antes de reenviar.")

        prefijo_texto = "Ajustes realizados:"
        prefijo_html = "<p><strong>Ajustes realizados</strong></p>"
        if prefijo_texto not in nota_texto:
            nota_texto = f"{prefijo_texto} {nota_texto}".strip()
        if "Ajustes realizados" not in nota_html:
            nota_html = f"{prefijo_html}{nota_html}"

        AgregarObservacionSolicitud(self._solicitudes, storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="solicitante",
            archivos=archivos or [],
        )

        solicitud.estado = EstadoSolicitudGestion.SOLICITUD
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.SOLICITUD,
            usuario_id=actor.id,
            comentario="Reenviada a primera aprobación tras ajustes del solicitante",
        )
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        resultado = refreshed or actualizada
        if self._notificador:
            self._notificador.notificar_revision_reenviada(resultado, actor)
        return resultado

    @staticmethod
    def _aplicar_ajustes_campos(
        solicitud: SolicitudGestion,
        *,
        titulo: str | None,
        proveedor_sugerido: str | None,
        descripcion_servicio: str | None,
        descripcion_servicio_texto: str | None,
        observaciones: str | None,
        observaciones_texto: str | None,
        centro_costo_area: str | None,
    ) -> None:
        """Aplica sólo los campos que el solicitante envió (None = no tocar)."""
        from html import escape

        if titulo is not None:
            t = titulo.strip()
            if t:
                solicitud.titulo = t
        if proveedor_sugerido is not None:
            solicitud.proveedor_sugerido = proveedor_sugerido.strip()
        if centro_costo_area is not None:
            cc = centro_costo_area.strip()
            if cc:
                solicitud.centro_costo_area = cc
        if descripcion_servicio_texto is not None:
            texto = descripcion_servicio_texto.strip()
            html = (descripcion_servicio or "").strip()
            if texto or html:
                solicitud.descripcion_servicio_texto = texto
                solicitud.descripcion_servicio = html or f"<p>{escape(texto)}</p>"
        elif descripcion_servicio is not None:
            html = descripcion_servicio.strip()
            if html:
                solicitud.descripcion_servicio = html
        if observaciones_texto is not None:
            texto = observaciones_texto.strip()
            html = (observaciones or "").strip()
            solicitud.observaciones_texto = texto
            solicitud.observaciones = html or (f"<p>{escape(texto)}</p>" if texto else "")
        elif observaciones is not None:
            solicitud.observaciones = observaciones.strip()

