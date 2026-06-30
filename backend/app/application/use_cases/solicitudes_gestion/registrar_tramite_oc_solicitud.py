"""Registra trámite OC general y/o parcial por ítem y avanza el flujo."""

from decimal import Decimal, InvalidOperation

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
from app.application.use_cases.solicitudes_gestion.avanzar_flujo_post_oc import (
    avanzar_a_items_en_camino,
)
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


def _parse_valor_tramite(raw: str | None) -> Decimal | None:
    texto = (raw or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        valor = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError("El valor del trámite OC no es un número válido.") from exc
    if valor < 0:
        raise ValueError("El valor del trámite OC debe ser mayor o igual a cero.")
    return valor


def _parse_porcentaje(raw: str | None) -> Decimal | None:
    texto = (raw or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        pct = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError("El porcentaje de anticipo no es un número válido.") from exc
    if pct <= 0 or pct > 100:
        raise ValueError("El porcentaje de anticipo debe estar entre 0.01 y 100.")
    return pct


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
        valor_tramite_oc: str = "",
        numeros_por_producto: dict[int, str] | None = None,
        valores_por_producto: dict[int, str] | None = None,
        requiere_anticipo: bool = False,
        porcentaje_anticipo: str = "",
        lider_anticipo_id: str = "",
        lider_anticipo_label: str = "",
        observaciones_anticipo: str = "",
        nueva_observacion: str = "",
        nueva_observacion_texto: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden registrar trámite OC.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_salidas_almacen

        if es_flujo_salidas_almacen(solicitud.tipo):
            raise ValueError("Las salidas de almacén no requieren trámite OC.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.TRAMITANDO_OC:
            raise ValueError("La solicitud debe estar en estado Tramitando OC.")

        if solicitud.gestor_id and solicitud.gestor_id != actor.id and not actor.is_admin():
            raise UnauthorizedError("Sólo el gestor asignado puede registrar el trámite OC.")

        general = (numero_tramite_oc or "").strip()
        valor_general = _parse_valor_tramite(valor_tramite_oc)

        parciales: dict[int, str] = {}
        for producto_id, valor in (numeros_por_producto or {}).items():
            parciales[int(producto_id)] = (valor or "").strip()

        valores_parciales: dict[int, Decimal | None] = {}
        for producto_id, valor in (valores_por_producto or {}).items():
            valores_parciales[int(producto_id)] = _parse_valor_tramite(valor)

        if not general and not any(parciales.values()):
            raise ValueError(
                "Indica el número de trámite OC general o al menos uno parcial por ítem."
            )

        pct_anticipo: Decimal | None = None
        monto_anticipo: Decimal | None = None
        if requiere_anticipo:
            pct_anticipo = _parse_porcentaje(porcentaje_anticipo)
            if pct_anticipo is None:
                raise ValueError("Indica el porcentaje de anticipo requerido.")
            lider_id = (lider_anticipo_id or "").strip()
            lider_label = (lider_anticipo_label or "").strip()
            if not lider_id or not lider_label:
                raise ValueError("Selecciona el líder aprobador del anticipo.")
            base_oc = valor_general
            if base_oc is None and valores_parciales:
                total_parcial = Decimal("0")
                for v in valores_parciales.values():
                    if v is not None:
                        total_parcial += v
                if total_parcial > 0:
                    base_oc = total_parcial
            if base_oc is not None:
                monto_anticipo = (base_oc * pct_anticipo / Decimal("100")).quantize(
                    Decimal("0.01")
                )

        self._solicitudes.update_tramite_oc(
            solicitud_id,
            numero_tramite_oc=general,
            valor_tramite_oc=valor_general,
            numeros_por_producto=parciales if numeros_por_producto is not None else None,
            valores_por_producto=valores_parciales if valores_por_producto is not None else None,
        )

        solicitud.numero_tramite_oc = general
        if valor_general is not None:
            solicitud.valor_tramite_oc = valor_general

        solicitud.requiere_anticipo = requiere_anticipo
        solicitud.porcentaje_anticipo = pct_anticipo if requiere_anticipo else None
        solicitud.lider_anticipo_id = (lider_anticipo_id or "").strip() if requiere_anticipo else ""
        solicitud.lider_anticipo_label = (
            (lider_anticipo_label or "").strip() if requiere_anticipo else ""
        )
        solicitud.monto_anticipo = monto_anticipo if requiere_anticipo else None
        solicitud.observaciones_anticipo = (
            (observaciones_anticipo or "").strip() if requiere_anticipo else ""
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
            bloque = f"Trámite OC general: {general}"
            if valor_general is not None:
                bloque += f" (valor: {valor_general:,.2f})"
            partes.append(bloque)
        if parciales:
            for pid, num in parciales.items():
                if num:
                    bloque = f"Ítem #{pid}: {num}"
                    valor_item = valores_parciales.get(pid)
                    if valor_item is not None:
                        bloque += f" (valor: {valor_item:,.2f})"
                    partes.append(bloque)

        if requiere_anticipo and pct_anticipo is not None:
            bloque_ant = f"Anticipo solicitado: {pct_anticipo}%"
            if monto_anticipo is not None:
                bloque_ant += f" (monto: {monto_anticipo:,.2f})"
            bloque_ant += f" — Líder: {solicitud.lider_anticipo_label}"
            partes.append(bloque_ant)
            solicitud.estado = EstadoSolicitudGestion.APROBACION_ANTICIPO
            proxima = EstadoSolicitudGestion.APROBACION_ANTICIPO
            comentario_hist = f"Trámite OC registrado — {' · '.join(partes)}"
            self._solicitudes.update(solicitud)
            self._solicitudes.registrar_historial(
                solicitud_id,
                proxima,
                usuario_id=actor.id,
                comentario=comentario_hist,
            )
        else:
            comentario_hist = f"Orden OC registrada — {' · '.join(partes)}"
            self._solicitudes.update(solicitud)
            actualizada = avanzar_a_items_en_camino(
                self._solicitudes,
                solicitud_id,
                actor.id,
                comentario_tramitada=comentario_hist,
            )
            if actualizada is None:
                raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
            return actualizada

        actualizada = self._solicitudes.get_by_id(solicitud_id)
        if actualizada is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        return actualizada
