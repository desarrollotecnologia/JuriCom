"""Registra trámite OC general y/o parcial por ítem."""

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


class RegistrarTramiteOcSolicitud:
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
        numero_tramite_oc: str = "",
        numeros_por_producto: dict[int, str] | None = None,
        nueva_observacion: str = "",
        nueva_observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar trámite OC.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.TRAMITADA_OC:
            raise ValueError("La solicitud debe estar en estado Tramitada OC.")

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede registrar el trámite OC.")

        general = (numero_tramite_oc or "").strip()
        parciales: dict[int, str] = {}
        for producto_id, valor in (numeros_por_producto or {}).items():
            parciales[int(producto_id)] = (valor or "").strip()

        if not general and not any(parciales.values()):
            raise ValueError(
                "Indica el número de trámite OC general o al menos uno parcial por ítem."
            )

        self._solicitudes.update_tramite_oc(
            solicitud_id,
            numero_tramite_oc=general,
            numeros_por_producto=parciales if numeros_por_producto is not None else None,
        )

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

        partes: list[str] = []
        if general:
            partes.append(f"Trámite OC general: {general}")
        if parciales:
            for pid, num in parciales.items():
                if num:
                    partes.append(f"Ítem #{pid}: {num}")

        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.TRAMITADA_OC,
            usuario_id=actor.id,
            comentario=f"Orden OC registrada — {' · '.join(partes)}",
        )

        actualizada = self._solicitudes.get_by_id(solicitud_id)
        if actualizada is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        return actualizada
