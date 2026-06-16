"""Devuelve una solicitud a cotización por solicitud del líder en segunda aprobación."""

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
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class SolicitarRecotizacionSolicitud:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
        storage: FileStorage | None = None,
    ) -> SolicitudGestion:
        solicitud = self._get_en_segunda_aprobacion(actor, solicitud_id)

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        if not nota_texto and not nota_html:
            raise ValueError(
                "Debes indicar el motivo por el cual solicitas una nueva recotización."
            )

        prefijo_texto = "Solicitud de recotización:"
        prefijo_html = "<p><strong>Solicitud de recotización</strong></p>"
        if prefijo_texto not in nota_texto:
            nota_texto = f"{prefijo_texto} {nota_texto}".strip()
        if "Solicitud de recotización" not in nota_html:
            nota_html = f"{prefijo_html}{nota_html}"

        AgregarObservacionSolicitud(self._solicitudes, storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="aprobador_segunda",
            archivos=archivos or [],
        )

        solicitud.estado = EstadoSolicitudGestion.COTIZACION
        solicitud.lider_segunda_aprobacion_id = ""
        solicitud.lider_segunda_aprobacion_label = ""
        actualizada = self._solicitudes.update(solicitud)

        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.COTIZACION,
            usuario_id=actor.id,
            comentario="Devuelta a Cotización — solicitud de recotización",
        )
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return refreshed or actualizada

    def _get_en_segunda_aprobacion(self, actor: User, solicitud_id: int) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden solicitar recotización."
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if solicitud.tipo != TipoSolicitudGestion.COMPRA:
            raise ValueError("Sólo aplica a solicitudes de compra.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.EN_APROBACION:
            raise ValueError(
                "Sólo se puede solicitar recotización en la segunda aprobación."
            )

        if actor.is_compras() and not actor.is_admin() and solicitud.creado_por_id == actor.id:
            raise UnauthorizedError("No puedes gestionar la aprobación de tu propia solicitud.")

        return solicitud
