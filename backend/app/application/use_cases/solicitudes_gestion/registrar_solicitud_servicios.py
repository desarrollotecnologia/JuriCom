"""Registra una solicitud de servicios con adjuntos."""

from datetime import date

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
)
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class RegistrarSolicitudServicios:
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
        titulo: str,
        requiere_visita: bool,
        servicio_programado: bool,
        fecha_servicio_programado: date | None,
        descripcion_servicio: str,
        descripcion_servicio_texto: str,
        proveedor_sugerido: str,
        centro_costo_area: str,
        lider_area_id: str,
        lider_area_label: str,
        observaciones: str,
        observaciones_texto: str,
        archivos_detalle: list[ArchivoEntradaSolicitud],
        archivo_ficha_tecnica: ArchivoEntradaSolicitud | None,
        archivo_hoja_vida: ArchivoEntradaSolicitud | None,
        archivos_observaciones: list[ArchivoEntradaSolicitud],
    ) -> SolicitudGestion:
        if not actor.puede_crear_solicitudes_gestion():
            raise UnauthorizedError(
                "No tienes permiso para registrar solicitudes de servicios."
            )

        titulo = (titulo or "").strip()
        if not titulo:
            raise ValueError("El título o asunto del servicio es obligatorio.")
        if not centro_costo_area:
            raise ValueError("El centro de costo del área solicitante es obligatorio.")
        if not lider_area_id:
            raise ValueError("Debes seleccionar un líder aprobador.")

        descripcion_texto = (descripcion_servicio_texto or "").strip()
        descripcion_html = (descripcion_servicio or "").strip()
        if not descripcion_texto and not descripcion_html:
            raise ValueError("La descripción del servicio es obligatoria.")

        if servicio_programado and fecha_servicio_programado is None:
            raise ValueError(
                "Debes indicar la fecha cuando el servicio está programado."
            )

        solicitud = SolicitudGestion(
            tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
            titulo=titulo,
            presupuestado=None,
            centro_costo_area=centro_costo_area.strip(),
            lider_area_id=str(lider_area_id).strip(),
            lider_area_label=(lider_area_label or "").strip(),
            requiere_visita=requiere_visita,
            servicio_programado=servicio_programado,
            fecha_servicio_programado=fecha_servicio_programado
            if servicio_programado
            else None,
            descripcion_servicio=descripcion_html,
            descripcion_servicio_texto=descripcion_texto,
            proveedor_sugerido=(proveedor_sugerido or "").strip(),
            observaciones=observaciones or "",
            observaciones_texto=(observaciones_texto or "").strip(),
            creado_por_id=actor.id,
            creado_por_email=(actor.email or "").strip(),
            estado=EstadoSolicitudGestion.SOLICITUD,
        )

        entradas: list[ArchivoEntradaSolicitud] = []
        entradas.extend(archivos_detalle)
        if archivo_ficha_tecnica:
            entradas.append(archivo_ficha_tecnica)
        if archivo_hoja_vida:
            entradas.append(archivo_hoja_vida)
        entradas.extend(archivos_observaciones)

        for entrada in entradas:
            stored = self._storage.save(
                contenido=entrada.contenido,
                nombre_original=entrada.nombre_original,
                mime_type=entrada.mime_type,
                subcarpeta="solicitudes",
            )
            solicitud.archivos.append(
                SolicitudGestionArchivo(
                    nombre_original=stored.nombre_original,
                    ruta_almacenamiento=stored.ruta,
                    mime_type=stored.mime_type,
                    tamano_bytes=stored.tamano_bytes,
                    categoria=entrada.categoria or "solicitud",
                    subido_por_id=actor.id,
                )
            )

        created = self._solicitudes.create(solicitud)

        tiene_obs = (observaciones_texto or "").strip() or (observaciones or "").strip()
        tiene_archivos_obs = bool(archivos_observaciones)
        if tiene_obs or tiene_archivos_obs:
            from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
                AgregarObservacionSolicitud,
            )

            obs = AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                created.id,
                contenido=observaciones or "",
                contenido_texto=observaciones_texto or "",
                contexto_rol="solicitante",
            )
            if tiene_archivos_obs:
                refreshed = self._solicitudes.get_by_id(created.id)
                if refreshed:
                    archivo_ids = [
                        a.id
                        for a in refreshed.archivos
                        if a.id
                        and not a.observacion_id
                        and a.categoria == "solicitud"
                    ]
                    self._solicitudes.link_archivos_observacion(obs.id, archivo_ids)

        refreshed = self._solicitudes.get_by_id(created.id)
        resultado = refreshed or created
        if self._notificador:
            self._notificador.notificar_solicitud_creada(resultado, actor)
        return resultado
