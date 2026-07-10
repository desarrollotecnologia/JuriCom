"""Solicita anticipo para una solicitud de servicios en gestión."""

from decimal import Decimal

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
from app.application.use_cases.solicitudes_gestion.registrar_tramite_oc_solicitud import (
    _parse_porcentaje,
    _parse_valor_tramite,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios


class SolicitarAnticipoServiciosSolicitud:
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
        valor_servicio: str = "",
        porcentaje_anticipo: str = "",
        lider_anticipo_id: str = "",
        lider_anticipo_label: str = "",
        observaciones_anticipo: str = "",
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
            raise ValueError("La solicitud debe estar en estado Gestionando servicio.")

        if solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede solicitar el anticipo.")

        valor = _parse_valor_tramite(valor_servicio)
        if valor is None or valor <= 0:
            raise ValueError("Indica el valor del servicio para calcular el anticipo.")

        pct_anticipo = _parse_porcentaje(porcentaje_anticipo)
        if pct_anticipo is None:
            raise ValueError("Indica el porcentaje de anticipo requerido.")

        lider_id = (lider_anticipo_id or "").strip()
        lider_label = (lider_anticipo_label or "").strip()
        if not lider_id or not lider_label:
            raise ValueError("Selecciona el líder aprobador del anticipo.")

        monto_anticipo = (valor * pct_anticipo / Decimal("100")).quantize(Decimal("0.01"))

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or adjuntos_obs:
            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="gestor",
                archivos=adjuntos_obs,
            )

        solicitud.valor_tramite_oc = valor
        solicitud.requiere_anticipo = True
        solicitud.porcentaje_anticipo = pct_anticipo
        solicitud.lider_anticipo_id = lider_id
        solicitud.lider_anticipo_label = lider_label
        solicitud.monto_anticipo = monto_anticipo
        solicitud.observaciones_anticipo = (observaciones_anticipo or "").strip()
        solicitud.estado = EstadoSolicitudGestion.APROBACION_ANTICIPO
        self._solicitudes.update(solicitud)

        comentario = (
            f"Anticipo solicitado: {pct_anticipo}% sobre valor {valor:,.2f} "
            f"(monto: {monto_anticipo:,.2f}) — Líder: {lider_label}"
        )
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.APROBACION_ANTICIPO,
            usuario_id=actor.id,
            comentario=comentario,
        )

        resultado = self._solicitudes.get_by_id(solicitud_id)
        if resultado is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        if self._notificador:
            self._notificador.notificar_anticipo_solicitado(resultado, actor)
        return resultado
