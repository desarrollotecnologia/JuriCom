"""Notifica al solicitante para adjuntar evidencia y cerrar un servicio post-anticipo."""

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
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios


class NotificarEvidenciaCierreServiciosSolicitud:
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
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ):
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden gestionar servicios.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if not es_flujo_servicios(solicitud.tipo):
            raise ValueError("Esta acción solo aplica a solicitudes de servicios.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.GESTIONANDO_SERVICIO:
            raise ValueError(
                "La solicitud debe estar en estado Gestionando servicio para notificar evidencia."
            )

        if not (
            solicitud.anticipo_gestionado
            or (solicitud.gestion_valor_registrada and not solicitud.requiere_anticipo)
        ):
            raise ValueError(
                "Debes registrar el valor del servicio sin anticipo, o completar la "
                "gestión de anticipo, antes de notificar evidencia de cierre."
            )

        if solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede notificar al solicitante.")

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        adjuntos_obs = archivos_observacion or []

        if not nota_texto and not nota_html and not adjuntos_obs:
            raise ValueError(
                "Registra una observación del gestor antes de notificar al solicitante."
            )

        AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="gestor",
            archivos=adjuntos_obs,
        )

        solicitud.estado = EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE
        self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE,
            usuario_id=actor.id,
            comentario=(
                "Solicitante notificado para adjuntar evidencia y observación de cierre"
            ),
        )

        resultado = self._solicitudes.get_by_id(solicitud_id)
        if resultado is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        if self._notificador:
            self._notificador.notificar_evidencia_cierre_solicitado(resultado, actor)
        return resultado
