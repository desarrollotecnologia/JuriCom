"""Comité técnico: Proyectos revisa (y puede reescribir) la solicitud.

Tras la 1.ª aprobación, la SRV con comité técnico queda en `REVISION_PROYECTOS`.
Proyectos puede editar los datos de la solicitud y, al confirmar, la envía a
`COTIZACION_PROYECTOS` para adjuntar las cotizaciones del proyecto.
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
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.application.use_cases.solicitudes_gestion.responder_revision_solicitud import (
    ResponderRevisionSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios


def _bloque_proveedores(proveedor_sugerido: str | None) -> tuple[str, str]:
    """Arma un bloque de texto/HTML con los proveedores propuestos."""
    from html import escape

    texto = (proveedor_sugerido or "").strip()
    if not texto:
        return "", ""
    lineas = [
        ln.lstrip("-").strip() for ln in texto.splitlines() if ln.strip()
    ]
    lineas = [ln for ln in lineas if ln]
    if not lineas:
        return "", ""
    bloque_texto = "Proveedores propuestos:\n" + "\n".join(f"- {ln}" for ln in lineas)
    items = "".join(f"<li>{escape(ln)}</li>" for ln in lineas)
    bloque_html = (
        f"<p><strong>Proveedores propuestos</strong></p><ul>{items}</ul>"
    )
    return bloque_texto, bloque_html


class ResponderRevisionProyectos:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage | None = None,
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
        observacion: str = "",
        observacion_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
        titulo: str | None = None,
        proveedor_sugerido: str | None = None,
        descripcion_servicio: str | None = None,
        descripcion_servicio_texto: str | None = None,
        observaciones: str | None = None,
        observaciones_texto: str | None = None,
        centro_costo_area: str | None = None,
    ) -> SolicitudGestion:
        if not actor.puede_cotizar_proyectos():
            raise UnauthorizedError(
                "Sólo el rol Proyectos o Admin pueden revisar la solicitud aquí."
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_flujo_servicios(solicitud.tipo) or not bool(
            getattr(solicitud, "requiere_comite_tecnico", False)
        ):
            raise ValueError("Esta solicitud no requiere comité técnico.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.REVISION_PROYECTOS:
            raise ValueError("La solicitud no está en revisión de Proyectos.")

        if (
            solicitud.proyectista_id
            and solicitud.proyectista_id != actor.id
            and not actor.is_admin()
        ):
            raise UnauthorizedError("Esta solicitud ya la está revisando otro proyectista.")

        # Reutiliza la misma lógica de reescritura de campos del solicitante.
        ResponderRevisionSolicitud._aplicar_ajustes_campos(
            solicitud,
            titulo=titulo,
            proveedor_sugerido=proveedor_sugerido,
            descripcion_servicio=descripcion_servicio,
            descripcion_servicio_texto=descripcion_servicio_texto,
            observaciones=observaciones,
            observaciones_texto=observaciones_texto,
            centro_costo_area=centro_costo_area,
        )

        if not solicitud.proyectista_id:
            solicitud.proyectista_id = actor.id

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        adjuntos = archivos or []
        if not nota_texto and not nota_html:
            nota_texto = "Proyectos revisó la solicitud."
            nota_html = "<p>Proyectos revisó la solicitud.</p>"

        # Deja constancia de los proveedores propuestos en la trazabilidad de
        # observaciones, para que Compras y Proyectos los vean en el historial.
        bloque_texto, bloque_html = _bloque_proveedores(solicitud.proveedor_sugerido)
        if bloque_texto:
            nota_texto = f"{nota_texto}\n\n{bloque_texto}".strip()
            nota_html = f"{nota_html}{bloque_html}"

        AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="proyectos",
            archivos=adjuntos,
        )

        # Si el solicitante marcó "requiere visita", antes de cotizar Proyectos
        # debe agendar la visita (proveedor + fecha + hora).
        requiere_visita = bool(getattr(solicitud, "requiere_visita", False))
        destino = (
            EstadoSolicitudGestion.PROGRAMACION_VISITA
            if requiere_visita
            else EstadoSolicitudGestion.COTIZACION_PROYECTOS
        )
        comentario = (
            f"Proyectos revisó la solicitud y pasa a programar visita ({actor.username})."
            if requiere_visita
            else f"Proyectos revisó la solicitud y pasa a cotización ({actor.username})."
        )
        solicitud.estado = destino
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            destino,
            usuario_id=actor.id,
            comentario=comentario,
        )
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador and hasattr(
            self._notificador, "notificar_revision_proyectos_lista"
        ):
            self._notificador.notificar_revision_proyectos_lista(resultado, actor)
        return resultado
