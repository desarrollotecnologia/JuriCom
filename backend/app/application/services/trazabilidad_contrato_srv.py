"""Copia eventos del contrato al historial de la SRV vinculada."""

import logging

from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion

logger = logging.getLogger(__name__)

_ESTADO_CONTRATO_UI = {
    "en_proceso": "Pendiente",
    "elaborando": "Elaborando contrato",
    "revision_polizas": "Revisión de pólizas",
    "solicitud_firmas": "Solicitud de firmas",
    "anticipo_contabilidad": "Anticipo en contabilidad",
    "anticipo_tesoreria": "Anticipo en tesorería",
    "anticipo_pagado": "Anticipo pagado",
    "activo": "Activo",
    "finalizado": "Finalizado",
    "cierre_contabilidad": "Cierre en contabilidad",
    "cierre_tesoreria": "Cierre en tesorería",
    "completado": "Completado",
}

_ETAPA_HISTORIAL_POR_ESTADO = {
    "en_proceso": EstadoSolicitudGestion.EN_JURIDICA,
    "elaborando": EstadoSolicitudGestion.ELABORANDO_CONTRATO,
    "revision_polizas": EstadoSolicitudGestion.REVISION_POLIZAS,
    "solicitud_firmas": EstadoSolicitudGestion.SOLICITUD_FIRMAS,
    "anticipo_contabilidad": EstadoSolicitudGestion.ANTICIPO_CONTABILIDAD,
    "anticipo_tesoreria": EstadoSolicitudGestion.ANTICIPO_TESORERIA,
    "anticipo_pagado": EstadoSolicitudGestion.ANTICIPO_PAGADO,
    "activo": EstadoSolicitudGestion.CONTRATO_ACTIVO,
    "finalizado": EstadoSolicitudGestion.CONTRATO_FINALIZADO,
    "cierre_contabilidad": EstadoSolicitudGestion.CIERRE_CONTABILIDAD,
    "cierre_tesoreria": EstadoSolicitudGestion.CIERRE_TESORERIA,
    "completado": EstadoSolicitudGestion.CONTRATO_COMPLETADO,
}


def etiqueta_estado_contrato(estado) -> str:
    valor = getattr(estado, "value", estado) or ""
    return _ESTADO_CONTRATO_UI.get(str(valor), str(valor))


def etapa_historial_contrato(estado) -> EstadoSolicitudGestion:
    valor = getattr(estado, "value", estado) or ""
    return _ETAPA_HISTORIAL_POR_ESTADO.get(str(valor), EstadoSolicitudGestion.EN_JURIDICA)


def registrar_evento_contrato_en_srv(
    solicitudes, contrato, actor_id, comentario: str, etapa=None, nuevo_estado=None
) -> None:
    """No falla el flujo principal si la SRV no existe o el historial no se pudo escribir.

    Si se pasa ``nuevo_estado``, además de registrar el historial se actualiza el
    estado propio de la SRV (para que en el listado de Compras aparezca, p. ej.,
    como "Contrato finalizado" cuando el supervisor cierra la operación).
    """
    if solicitudes is None or contrato is None:
        return
    sid = getattr(contrato, "solicitud_gestion_id", None)
    if not sid:
        return
    texto = (comentario or "").strip()
    if not texto:
        return
    if len(texto) > 400:
        texto = texto[:397] + "..."
    try:
        solicitud = solicitudes.get_by_id(sid)
        if solicitud is None:
            return
        solicitudes.registrar_historial(
            solicitud.id,
            etapa or nuevo_estado or solicitud.estado,
            usuario_id=actor_id,
            comentario=texto,
        )
        if nuevo_estado is not None:
            solicitud.estado = nuevo_estado
            solicitudes.update(solicitud)
    except Exception:
        logger.exception(
            "No se pudo registrar el evento del contrato %s en la SRV %s",
            getattr(contrato, "codigo", None),
            sid,
        )


def registrar_observacion_contrato_en_srv(
    solicitudes,
    contrato,
    actor,
    texto: str,
    *,
    contexto: str = "juridica",
    archivos=None,
    contenido_html: str = "",
    storage=None,
) -> None:
    """Copia una observación libre del contrato al historial de observaciones de la SRV.

    ``archivos`` es una lista opcional de ``SolicitudGestionArchivo`` ya persistidos en
    el almacenamiento (se enlazan a la observación creada).
    ``contenido_html`` es el HTML enriquecido del editor (formato + imágenes inline).
    Si no se pasa, se usa ``texto`` escapado dentro de un ``<p>``.
    ``storage`` permite extraer las imágenes embebidas (data URI) del HTML y guardarlas
    como archivos, evitando que el base64 desborde la columna ``contenido``.
    No interrumpe el flujo principal si la SRV no existe o falla el guardado.
    """
    if solicitudes is None or contrato is None or actor is None:
        return
    sid = getattr(contrato, "solicitud_gestion_id", None)
    if not sid:
        return
    contenido = (texto or "").strip()
    html = (contenido_html or "").strip()
    adjuntos = list(archivos or [])
    if not contenido and not html and not adjuntos:
        return
    from html import escape

    from app.application.services.observacion_inline_images import (
        apply_pending_archivo_ids,
        extract_inline_images,
    )
    from app.domain.entities.solicitud_gestion import (
        SolicitudGestionArchivo,
        SolicitudGestionObservacion,
    )
    from app.domain.value_objects.rol_display import etiqueta_rol_usuario

    # Extrae imágenes embebidas (base64) para no guardarlas dentro de ``contenido``.
    inline_images = []
    if html and storage is not None:
        html, inline_images = extract_inline_images(html)

    if not contenido:
        contenido = "Evidencia adjunta."
    try:
        solicitud = solicitudes.get_by_id(sid)
        if solicitud is None:
            return
        creada = solicitudes.add_observacion(
            sid,
            SolicitudGestionObservacion(
                solicitud_id=sid,
                usuario_id=getattr(actor, "id", None),
                autor_nombre=getattr(actor, "username", "") or "",
                autor_rol=etiqueta_rol_usuario(actor, contexto=contexto),
                contenido=html or f"<p>{escape(contenido)}</p>",
                contenido_texto=contenido,
            ),
        )
        pending_to_id: dict[int, int] = {}
        if inline_images and storage is not None:
            entidades_inline = []
            for img in inline_images:
                stored = storage.save(
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
                        subido_por_id=getattr(actor, "id", None),
                    )
                )
            inline_ids = solicitudes.add_archivos(
                sid, entidades_inline, observacion_id=creada.id
            )
            pending_to_id = {idx: aid for idx, aid in enumerate(inline_ids)}
        if adjuntos:
            solicitudes.add_archivos(sid, adjuntos, observacion_id=creada.id)
        if pending_to_id:
            final_html = apply_pending_archivo_ids(
                html or f"<p>{escape(contenido)}</p>", pending_to_id
            )
            solicitudes.update_observacion_contenido(creada.id, final_html)
    except Exception:
        logger.exception(
            "No se pudo registrar la observación del contrato %s en la SRV %s",
            getattr(contrato, "codigo", None),
            sid,
        )
