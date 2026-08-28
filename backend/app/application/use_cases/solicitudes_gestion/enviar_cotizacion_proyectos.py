"""Comité técnico: el rol Proyectos cotiza antes de que Compras complete.

Proyectos toma la SRV (tras la 1.ª aprobación) y adjunta 1+ cotizaciones con
observación opcional. Al "enviar a Compras" la SRV pasa a estado Cotización,
donde Compras la completa (mínimo 3) y la manda a la 2.ª aprobación.
"""

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
from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
    _aplicar_datos_economicos_srv,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios


class EnviarCotizacionProyectos:
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
        cotizaciones: list[ArchivoEntradaSolicitud] | None = None,
        nueva_observacion: str = "",
        nueva_observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
        enviar: bool = False,
    ) -> SolicitudGestion:
        if not actor.puede_cotizar_proyectos():
            raise UnauthorizedError("Sólo el rol Proyectos o Admin pueden cotizar aquí.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_flujo_servicios(solicitud.tipo) or not bool(
            getattr(solicitud, "requiere_comite_tecnico", False)
        ):
            raise ValueError("Esta solicitud no requiere comité técnico.")

        estado = normalizar_estado(solicitud.estado)
        if estado != EstadoSolicitudGestion.COTIZACION_PROYECTOS:
            raise ValueError(
                "Proyectos sólo cotiza en la etapa de Cotización (Proyectos), "
                "tras revisar la solicitud."
            )

        # Bloqueo simple: si ya la tomó otro proyectista, no dejar operar.
        if (
            solicitud.proyectista_id
            and solicitud.proyectista_id != actor.id
            and not actor.is_admin()
        ):
            raise UnauthorizedError("Esta solicitud ya la está cotizando otro proyectista.")

        # Toma la solicitud si aún no tiene proyectista.
        if not solicitud.proyectista_id:
            solicitud.proyectista_id = actor.id

        cotizaciones = cotizaciones or []
        _aplicar_datos_economicos_srv(cotizaciones)

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
                    valor_cotizacion=entrada.valor_cotizacion,
                    moneda_cotizacion=entrada.moneda_cotizacion or "COP",
                    requiere_anticipo=entrada.requiere_anticipo,
                    porcentaje_anticipo=entrada.porcentaje_anticipo,
                    monto_anticipo=entrada.monto_anticipo,
                    propuesta=entrada.propuesta,
                )
            )
        if archivos_nuevos:
            nuevos_ids = self._solicitudes.add_archivos(solicitud_id, archivos_nuevos)

        self._solicitudes.update(solicitud)

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or nuevos_ids or adjuntos_obs:
            if not nota_texto and not nota_html and (nuevos_ids or adjuntos_obs):
                nota_html = "<p>Cotizaciones de Proyectos.</p>"
                nota_texto = "Cotizaciones de Proyectos."
            obs = AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="proyectos",
                archivos=adjuntos_obs,
            )
            if nuevos_ids:
                self._solicitudes.link_archivos_observacion(obs.id, nuevos_ids)

        if not enviar:
            self._solicitudes.registrar_historial(
                solicitud_id,
                EstadoSolicitudGestion.COTIZACION_PROYECTOS,
                usuario_id=actor.id,
                comentario=f"Proyectos adjuntó cotizaciones ({actor.username}).",
            )
            return self._solicitudes.get_by_id(solicitud_id) or solicitud

        total = self._solicitudes.count_archivos_categoria(solicitud_id, "cotizacion")
        if total < 1:
            raise ValueError("Adjunta al menos una cotización antes de enviar a Compras.")

        # Si el servicio requiere visita, antes de que Compras complete cotizaciones
        # debe programar su propia visita (2.ª visita del comité).
        requiere_visita = bool(getattr(solicitud, "requiere_visita", False))
        destino = (
            EstadoSolicitudGestion.PROGRAMACION_VISITA
            if requiere_visita
            else EstadoSolicitudGestion.COTIZACION
        )
        solicitud.estado = destino
        actualizada = self._solicitudes.update(solicitud)
        comentario = (
            f"Proyectos envió {total} cotización(es); Compras programa visita."
            if requiere_visita
            else f"Proyectos envió {total} cotización(es) a Compras."
        )
        self._solicitudes.registrar_historial(
            solicitud_id,
            destino,
            usuario_id=actor.id,
            comentario=comentario,
        )
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador:
            self._notificador.notificar_cotizacion_proyectos_enviada(resultado, actor)
        return resultado
