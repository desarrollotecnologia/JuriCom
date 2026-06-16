"""Agrega un comentario al historial de trazabilidad de una solicitud."""

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.use_cases.solicitudes_gestion.get_solicitud_gestion import (
    GetSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestionArchivo,
    SolicitudGestionObservacion,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.application.services.observacion_inline_images import (
    apply_pending_archivo_ids,
    extract_inline_images,
)
from app.domain.value_objects.rol_display import etiqueta_rol_usuario


class AgregarObservacionSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage
        self._get = GetSolicitudGestion(solicitudes)

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        contenido: str,
        contenido_texto: str = "",
        contexto_rol: str = "default",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
        categoria_archivos: str = "observacion",
    ) -> SolicitudGestionObservacion:
        self._get.execute(actor, solicitud_id)

        adjuntos = archivos or []
        texto = (contenido_texto or "").strip()
        html = (contenido or "").strip()
        inline_images = []

        if html and self._storage is not None:
            html, inline_images = extract_inline_images(html)

        if not texto and not html and not adjuntos and not inline_images:
            raise ValueError("El comentario no puede estar vacío.")

        if not html and not texto:
            html = "<p>Archivos adjuntos.</p>"
            texto = "Archivos adjuntos."
        elif not html:
            from html import escape

            html = f"<p>{escape(texto)}</p>"

        observacion = SolicitudGestionObservacion(
            solicitud_id=solicitud_id,
            usuario_id=actor.id,
            autor_nombre=actor.username,
            autor_rol=etiqueta_rol_usuario(actor, contexto=contexto_rol),
            contenido=html,
            contenido_texto=texto or html,
        )
        created = self._solicitudes.add_observacion(solicitud_id, observacion)

        pending_to_id: dict[int, int] = {}
        if inline_images:
            if self._storage is None:
                raise ValueError("No se configuró almacenamiento para imágenes embebidas.")
            entidades_inline: list[SolicitudGestionArchivo] = []
            for img in inline_images:
                stored = self._storage.save(
                    contenido=img.contenido,
                    nombre_original=img.nombre,
                    mime_type=f"image/{img.mime_subtype}",
                    subcarpeta="solicitudes/observaciones/inline",
                )
                entidades_inline.append(
                    SolicitudGestionArchivo(
                        nombre_original=stored.nombre_original,
                        ruta_almacenamiento=stored.ruta,
                        mime_type=stored.mime_type,
                        tamano_bytes=stored.tamano_bytes,
                        categoria="observacion_inline",
                        subido_por_id=actor.id,
                    )
                )
            inline_ids = self._solicitudes.add_archivos(
                solicitud_id, entidades_inline, observacion_id=created.id
            )
            pending_to_id = {idx: aid for idx, aid in enumerate(inline_ids)}

        if adjuntos:
            if self._storage is None:
                raise ValueError("No se configuró almacenamiento para adjuntos.")
            entidades: list[SolicitudGestionArchivo] = []
            for entrada in adjuntos:
                stored = self._storage.save(
                    contenido=entrada.contenido,
                    nombre_original=entrada.nombre_original,
                    mime_type=entrada.mime_type,
                    subcarpeta="solicitudes/observaciones",
                )
                entidades.append(
                    SolicitudGestionArchivo(
                        nombre_original=stored.nombre_original,
                        ruta_almacenamiento=stored.ruta,
                        mime_type=stored.mime_type,
                        tamano_bytes=stored.tamano_bytes,
                        categoria=categoria_archivos,
                        subido_por_id=actor.id,
                    )
                )
            self._solicitudes.add_archivos(
                solicitud_id, entidades, observacion_id=created.id
            )

        if pending_to_id:
            final_html = apply_pending_archivo_ids(html, pending_to_id)
            self._solicitudes.update_observacion_contenido(created.id, final_html)

        return self._solicitudes.get_observacion_by_id(created.id) or created
