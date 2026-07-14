"""Guarda programación de visitas sin enviar cotizaciones (servicios en Cotización)."""

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
    _parse_visitas_programadas,
    _validar_visitas_servicios,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


class GuardarGestionServiciosSolicitud:
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
        visitas_json: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ):
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden gestionar servicios.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios

        if not es_flujo_servicios(solicitud.tipo):
            raise ValueError("Esta acción solo aplica a solicitudes de servicios.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.COTIZACION:
            raise ValueError("La solicitud debe estar en estado Cotización.")

        if solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede guardar la gestión.")

        visitas = _parse_visitas_programadas(visitas_json)
        _validar_visitas_servicios(solicitud, visitas)

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or adjuntos_obs:
            if not nota_texto and not nota_html and adjuntos_obs:
                nota_html = "<p>Archivos adjuntos.</p>"
                nota_texto = "Archivos adjuntos."
            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="gestor",
                archivos=adjuntos_obs,
            )

        self._solicitudes.replace_visitas_programadas(solicitud_id, visitas)

        comentario = "Programación de visitas guardada"
        if visitas:
            comentario += f" ({len(visitas)} visita{'s' if len(visitas) != 1 else ''})"

        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.COTIZACION,
            usuario_id=actor.id,
            comentario=comentario,
        )

        resultado = self._solicitudes.get_by_id(solicitud_id)
        if resultado is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        return resultado
