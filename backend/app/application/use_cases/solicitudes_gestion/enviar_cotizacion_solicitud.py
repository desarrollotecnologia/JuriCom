"""Envía cotizaciones y solicita segunda aprobación."""

import json
from datetime import date, time

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
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
    SolicitudGestionVisitaProgramada,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)

MIN_COTIZACIONES = 3


def _parse_visitas_programadas(visitas_json: str) -> list[SolicitudGestionVisitaProgramada]:
    if not (visitas_json or "").strip():
        return []
    try:
        raw = json.loads(visitas_json)
    except json.JSONDecodeError as e:
        raise ValueError("El formato de visitas programadas no es válido.") from e
    if not isinstance(raw, list):
        raise ValueError("El formato de visitas programadas no es válido.")

    visitas: list[SolicitudGestionVisitaProgramada] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Visita {i}: formato inválido.")
        proveedor = str(item.get("proveedor_visita") or "").strip()
        fecha_raw = str(item.get("fecha_visita") or "").strip()
        hora_raw = str(item.get("hora_visita") or "").strip()
        if not proveedor and not fecha_raw and not hora_raw:
            continue
        fecha_visita: date | None = None
        hora_visita: time | None = None
        if fecha_raw:
            try:
                fecha_visita = date.fromisoformat(fecha_raw)
            except ValueError as e:
                raise ValueError(f"Visita {i}: la fecha no es válida.") from e
        if hora_raw:
            try:
                hora_visita = time.fromisoformat(hora_raw)
            except ValueError as e:
                raise ValueError(f"Visita {i}: la hora no es válida.") from e
        visitas.append(
            SolicitudGestionVisitaProgramada(
                programador_visita="",
                proveedor_visita=proveedor,
                fecha_visita=fecha_visita,
                hora_visita=hora_visita,
            )
        )
    return visitas


def _validar_visitas_servicios(
    solicitud: SolicitudGestion, visitas: list[SolicitudGestionVisitaProgramada]
) -> None:
    from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios

    if not es_flujo_servicios(solicitud.tipo):
        return
    if not visitas:
        return
    for i, visita in enumerate(visitas, start=1):
        if not (visita.proveedor_visita or "").strip():
            raise ValueError(f"Visita {i}: el proveedor de la visita es obligatorio.")
        if visita.fecha_visita is None:
            raise ValueError(f"Visita {i}: la fecha de visita es obligatoria.")


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
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage
        self._notificador = notificador

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
        visitas_json: str = "",
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

        visitas = _parse_visitas_programadas(visitas_json)
        _validar_visitas_servicios(solicitud, visitas)

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
        self._solicitudes.replace_visitas_programadas(solicitud_id, visitas)
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
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador:
            self._notificador.notificar_cotizacion_enviada(resultado, actor)
        return resultado
