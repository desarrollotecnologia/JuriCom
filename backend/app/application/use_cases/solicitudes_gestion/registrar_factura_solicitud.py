"""Registra facturas internas de una solicitud entregada (admite historial múltiple)."""

from datetime import datetime

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


class RegistrarFacturaSolicitud:
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
        observacion: str = "",
        observacion_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
    ) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar facturas.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        estado_actual = normalizar_estado(solicitud.estado)
        ya_tiene_factura = (
            solicitud.factura_registrada_at is not None
            or solicitud.cantidad_facturas > 0
            or estado_actual == EstadoSolicitudGestion.FACTURADA
        )
        if estado_actual not in (
            EstadoSolicitudGestion.ENTREGADO,
            EstadoSolicitudGestion.FACTURADA,
        ):
            raise ValueError(
                "Sólo se pueden registrar facturas en solicitudes Entregadas o Facturadas."
            )

        adjuntos = archivos or []
        if not adjuntos:
            raise ValueError("Debes adjuntar al menos un archivo de la factura.")

        es_adicional = ya_tiene_factura
        numero_factura = solicitud.cantidad_facturas + 1

        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        if not nota_texto and not nota_html:
            if es_adicional:
                nota_texto = f"Factura adicional #{numero_factura} registrada por Compras."
                nota_html = f"<p>{nota_texto}</p>"
            else:
                nota_texto = "Factura registrada por Compras."
                nota_html = "<p>Factura registrada por Compras.</p>"

        AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="gestor",
            archivos=adjuntos,
            categoria_archivos="factura",
        )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")

        if not es_adicional:
            solicitud.factura_registrada_at = datetime.utcnow()
            solicitud.factura_registrada_por_id = actor.id
            solicitud.estado = EstadoSolicitudGestion.FACTURADA
            comentario_hist = f"Factura registrada por {actor.username}"
        else:
            comentario_hist = (
                f"Factura adicional #{numero_factura} registrada por {actor.username}"
            )

        actualizada = self._solicitudes.update(solicitud)

        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.FACTURADA,
            usuario_id=actor.id,
            comentario=comentario_hist,
        )

        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return refreshed or actualizada
