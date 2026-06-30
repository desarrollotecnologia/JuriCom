"""Envía cotizaciones y solicita segunda aprobación."""

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion, SolicitudGestionArchivo
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)

MIN_COTIZACIONES = 3


def _append_justificacion_a_observacion(
    nota_html: str, nota_texto: str, justificacion: str
) -> tuple[str, str]:
    from html import escape

    j = (justificacion or "").strip()
    if not j:
        return nota_html, nota_texto

    texto_bloque = f"Justificación cotizaciones: {j}"
    html_bloque = (
        f'<p class="sg-justificacion-cotizaciones">'
        f"<strong>Justificación cotizaciones:</strong> "
        f"{escape(j).replace(chr(10), '<br>')}</p>"
    )

    texto = (nota_texto or "").strip()
    html = (nota_html or "").strip()

    if texto_bloque not in texto:
        texto = f"{texto}\n\n{texto_bloque}".strip() if texto else texto_bloque
    if j not in html:
        html = f"{html}{html_bloque}" if html else html_bloque

    return html, texto


class EnviarCotizacionSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        nueva_observacion: str = "",
        nueva_observacion_texto: str = "",
        justificacion: str = "",
        lider_segunda_aprobacion_id: str,
        lider_segunda_aprobacion_label: str,
        cotizaciones: list[ArchivoEntradaSolicitud],
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden enviar cotizaciones.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen

        if es_flujo_salidas_almacen(solicitud.tipo):
            raise ValueError("Las salidas de almacén no requieren cotización.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.COTIZACION:
            raise ValueError("La solicitud debe estar en estado Cotización.")

        if solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede enviar la cotización.")

        if not lider_segunda_aprobacion_id.strip():
            raise ValueError("Debes seleccionar un líder Colbeef para la segunda aprobación.")

        nuevos_ids: list[int] = []
        archivos_nuevos: list[SolicitudGestionArchivo] = []
        for entrada in cotizaciones:
            stored = self._storage.save(
                contenido=entrada.contenido,
                nombre_original=entrada.nombre_original,
                mime_type=entrada.mime_type,
                subcarpeta="solicitudes/cotizaciones",
            )
            archivos_nuevos.append(
                SolicitudGestionArchivo(
                    nombre_original=stored.nombre_original,
                    ruta_almacenamiento=stored.ruta,
                    mime_type=stored.mime_type,
                    tamano_bytes=stored.tamano_bytes,
                    categoria="cotizacion",
                    subido_por_id=actor.id,
                )
            )

        if archivos_nuevos:
            nuevos_ids = self._solicitudes.add_archivos(solicitud_id, archivos_nuevos)

        total_cotizaciones = self._solicitudes.count_archivos_categoria(
            solicitud_id, "cotizacion"
        )
        if total_cotizaciones < MIN_COTIZACIONES:
            justificacion = (justificacion or "").strip()
            if not justificacion:
                raise ValueError(
                    f"Debes adjuntar al menos {MIN_COTIZACIONES} cotizaciones o "
                    "indicar una justificación."
                )
            solicitud.justificacion_cotizaciones = justificacion

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        if solicitud.justificacion_cotizaciones:
            nota_html, nota_texto = _append_justificacion_a_observacion(
                nota_html, nota_texto, solicitud.justificacion_cotizaciones
            )
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or nuevos_ids or adjuntos_obs:
            if not nota_texto and not nota_html and (nuevos_ids or adjuntos_obs):
                nota_html = "<p>Adjunto cotizaciones.</p>" if nuevos_ids else "<p>Archivos adjuntos.</p>"
                nota_texto = "Adjunto cotizaciones." if nuevos_ids else "Archivos adjuntos."
            obs = AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="gestor",
                archivos=adjuntos_obs,
            )
            if nuevos_ids:
                self._solicitudes.link_archivos_observacion(obs.id, nuevos_ids)

        solicitud.lider_segunda_aprobacion_id = lider_segunda_aprobacion_id.strip()
        solicitud.lider_segunda_aprobacion_label = (lider_segunda_aprobacion_label or "").strip()
        solicitud.estado = EstadoSolicitudGestion.EN_APROBACION
        actualizada = self._solicitudes.update(solicitud)

        comentario = (
            f"Enviada a segunda aprobación — Líder: {solicitud.lider_segunda_aprobacion_label}"
        )
        if total_cotizaciones < MIN_COTIZACIONES:
            comentario += f" (Justificación: {solicitud.justificacion_cotizaciones})"

        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.EN_APROBACION,
            usuario_id=actor.id,
            comentario=comentario,
        )
        return self._solicitudes.get_by_id(solicitud_id) or actualizada
