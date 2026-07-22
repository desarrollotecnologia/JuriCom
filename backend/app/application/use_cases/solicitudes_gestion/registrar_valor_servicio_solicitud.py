"""Registra el valor cotizado de un servicio y su clasificación documental."""

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
from app.application.use_cases.solicitudes_gestion.registrar_tramite_oc_solicitud import (
    _parse_valor_tramite,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.clasificacion_documento_servicio import (
    clasificar_documento_servicio,
    label_clasificacion_documento_servicio,
)
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios


class RegistrarValorServicioSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        valor_servicio: str = "",
        requiere_anticipo: bool = False,
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

        if solicitud.anticipo_gestionado:
            raise ValueError(
                "El anticipo de este servicio ya fue gestionado; no se puede recalcular el valor."
            )

        if solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError(
                "Sólo el gestor asignado puede registrar el valor del servicio."
            )

        valor = _parse_valor_tramite(valor_servicio)
        if valor is None or valor <= 0:
            raise ValueError("Indica el valor total de la cotización del servicio.")

        clasificacion = clasificar_documento_servicio(valor)
        label = label_clasificacion_documento_servicio(clasificacion)

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or adjuntos_obs:
            if self._storage is None:
                raise ValueError("No se pueden guardar adjuntos sin almacenamiento.")
            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="gestor",
                archivos=adjuntos_obs,
            )

        solicitud.valor_tramite_oc = valor
        solicitud.clasificacion_documento_servicio = clasificacion.value
        solicitud.gestion_valor_registrada = True
        solicitud.requiere_anticipo = bool(requiere_anticipo)

        if not requiere_anticipo:
            solicitud.porcentaje_anticipo = None
            solicitud.lider_anticipo_id = ""
            solicitud.lider_anticipo_label = ""
            solicitud.monto_anticipo = None
            solicitud.observaciones_anticipo = ""

        self._solicitudes.update(solicitud)

        anticipo_txt = "con anticipo" if requiere_anticipo else "sin anticipo"
        comentario = (
            f"Valor del servicio registrado: {valor:,.2f} — {label} ({anticipo_txt})"
        )
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.GESTIONANDO_SERVICIO,
            usuario_id=actor.id,
            comentario=comentario,
        )

        resultado = self._solicitudes.get_by_id(solicitud_id)
        if resultado is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        return resultado
