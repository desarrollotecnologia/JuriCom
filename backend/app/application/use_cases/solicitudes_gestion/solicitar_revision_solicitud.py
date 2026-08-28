"""Primera aprobación: el aprobador devuelve la solicitud al solicitante para
que la ajuste (estado 'revisión'), indicando qué debe corregir."""

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
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class SolicitarRevisionSolicitud:
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
    ) -> SolicitudGestion:
        solicitud = self._get_en_primera_aprobacion(actor, solicitud_id)

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        if not nota_texto and not nota_html:
            raise ValueError(
                "Debes indicar qué debe ajustar el solicitante antes de devolverla."
            )

        prefijo_texto = "Ajustes solicitados:"
        prefijo_html = "<p><strong>Ajustes solicitados</strong></p>"
        if prefijo_texto not in nota_texto:
            nota_texto = f"{prefijo_texto} {nota_texto}".strip()
        if "Ajustes solicitados" not in nota_html:
            nota_html = f"{prefijo_html}{nota_html}"

        AgregarObservacionSolicitud(self._solicitudes, storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="aprobador_primera",
            archivos=archivos or [],
        )

        solicitud.estado = EstadoSolicitudGestion.REVISION
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.REVISION,
            usuario_id=actor.id,
            comentario="Devuelta al solicitante para ajustes",
        )
        refreshed = self._solicitudes.get_by_id(solicitud_id)
        resultado = refreshed or actualizada
        if self._notificador:
            self._notificador.notificar_solicitud_en_revision(resultado, actor)
        return resultado

    def _get_en_primera_aprobacion(
        self, actor: User, solicitud_id: int
    ) -> SolicitudGestion:
        if not actor.puede_aprobar_solicitudes_gestion():
            raise UnauthorizedError("No tienes permiso para devolver solicitudes a revisión.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if solicitud.tipo not in (
            TipoSolicitudGestion.COMPRA,
            TipoSolicitudGestion.SALIDAS_ALMACEN,
            TipoSolicitudGestion.INSUMOS_SERVICIOS,
        ):
            raise ValueError(
                "Sólo aplica a solicitudes de compra, salidas de almacén o servicios."
            )

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.SOLICITUD:
            raise ValueError(
                "Sólo se puede solicitar ajustes en la primera aprobación."
            )

        if (
            actor.is_lider_aprobador()
            and not actor.is_admin()
            and solicitud.creado_por_id == actor.id
        ):
            raise UnauthorizedError("No puedes gestionar tu propia solicitud.")

        if actor.is_lider_aprobador() and not actor.is_admin():
            if not actor.solicitud_asignada_a_lider(solicitud):
                raise UnauthorizedError(
                    "Esta solicitud no está asignada a usted como líder aprobador."
                )

        return solicitud
