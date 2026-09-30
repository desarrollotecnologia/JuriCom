"""Editar una solicitud antes de la primera aprobación (corrección del solicitante).

Solo el creador puede editar y solo mientras la solicitud sigue en estado
"Solicitud" (aún no ha pasado la primera aprobación). El cambio queda registrado
en la trazabilidad con el detalle de qué se modificó.
"""

import json
from decimal import Decimal, InvalidOperation
from html import escape

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.observacion_inline_images import html_sin_data_uri
from app.domain.entities.solicitud_gestion import (
    normalizar_prioridad,
    SolicitudGestion,
    SolicitudGestionProducto,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


def _fmt_cantidad(cantidad: Decimal) -> str:
    if cantidad == cantidad.to_integral_value():
        return str(int(cantidad))
    return format(cantidad.normalize(), "f").rstrip("0").rstrip(".") or "0"


def _parse_productos(productos_json: str) -> list[SolicitudGestionProducto]:
    try:
        productos_raw = json.loads(productos_json or "[]")
    except json.JSONDecodeError as e:
        raise ValueError("El detalle de productos no es válido.") from e
    if not isinstance(productos_raw, list) or not productos_raw:
        raise ValueError("Debes dejar al menos un producto.")

    productos: list[SolicitudGestionProducto] = []
    for i, item in enumerate(productos_raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Producto {i}: formato inválido.")
        descripcion = str(item.get("descripcion") or "").strip()
        unidad = str(item.get("unidad") or "").strip()
        centro = str(item.get("centro_costo") or "").strip()
        if not descripcion:
            raise ValueError(f"Producto {i}: la descripción es obligatoria.")
        if not unidad:
            raise ValueError(f"Producto {i}: la unidad es obligatoria.")
        if not centro:
            raise ValueError(f"Producto {i}: el centro de costo es obligatorio.")
        try:
            cantidad = Decimal(str(item.get("cantidad", 1)).replace(",", ".").strip() or "1")
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Producto {i}: cantidad inválida.") from e
        if cantidad <= 0:
            raise ValueError(f"Producto {i}: la cantidad debe ser mayor a cero.")
        productos.append(
            SolicitudGestionProducto(
                codigo_siimed=str(item.get("codigo_siimed") or "").strip(),
                unidad=unidad,
                descripcion=descripcion,
                centro_costo=centro,
                area_consumo=str(item.get("area_consumo") or "").strip(),
                cantidad=cantidad,
                estado_aprobacion=EstadoAprobacionProducto.PENDIENTE,
            )
        )
    return productos


class EditarSolicitudGestion:
    def __init__(self, solicitudes: SolicitudGestionRepository) -> None:
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        titulo: str | None = None,
        centro_costo_area: str | None = None,
        prioridad: str | None = None,
        presupuestado: bool | None = None,
        lider_area_id: str | None = None,
        lider_area_label: str | None = None,
        observaciones: str | None = None,
        observaciones_texto: str | None = None,
        proveedor_sugerido: str | None = None,
        descripcion_servicio: str | None = None,
        descripcion_servicio_texto: str | None = None,
        productos_json: str | None = None,
    ) -> SolicitudGestion:
        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        if solicitud.creado_por_id != actor.id:
            raise UnauthorizedError(
                "Sólo quien creó la solicitud puede editarla."
            )

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.SOLICITUD:
            raise ValueError(
                "Solo puedes editar la solicitud antes de la primera aprobación."
            )

        cambios: list[str] = []
        es_servicio = solicitud.tipo == TipoSolicitudGestion.INSUMOS_SERVICIOS

        if titulo is not None:
            nuevo = titulo.strip()
            if not nuevo:
                raise ValueError("El título o asunto no puede quedar vacío.")
            if nuevo != (solicitud.titulo or ""):
                cambios.append(f"Título: «{solicitud.titulo}» → «{nuevo}»")
                solicitud.titulo = nuevo

        if centro_costo_area is not None:
            nuevo = centro_costo_area.strip()
            if not nuevo:
                raise ValueError("El centro de costo no puede quedar vacío.")
            if nuevo != (solicitud.centro_costo_area or ""):
                cambios.append(
                    f"Centro de costo: «{solicitud.centro_costo_area}» → «{nuevo}»"
                )
                solicitud.centro_costo_area = nuevo

        if prioridad is not None:
            nuevo = normalizar_prioridad(prioridad)
            if nuevo != (solicitud.prioridad or "media"):
                cambios.append(f"Prioridad: {solicitud.prioridad} → {nuevo}")
                solicitud.prioridad = nuevo

        if presupuestado is not None and presupuestado != solicitud.presupuestado:
            cambios.append(
                f"Presupuestado: {'Sí' if presupuestado else 'No'}"
            )
            solicitud.presupuestado = presupuestado

        if lider_area_id is not None:
            nuevo_id = lider_area_id.strip()
            if not nuevo_id:
                raise ValueError("Debes seleccionar un líder de área.")
            if nuevo_id != (solicitud.lider_area_id or ""):
                anterior = solicitud.lider_area_label or solicitud.lider_area_id
                nuevo_label = (lider_area_label or "").strip() or nuevo_id
                cambios.append(f"Líder de área: «{anterior}» → «{nuevo_label}»")
                solicitud.lider_area_id = nuevo_id
                solicitud.lider_area_label = nuevo_label

        if observaciones_texto is not None:
            texto = observaciones_texto.strip()
            html = html_sin_data_uri((observaciones or "").strip())
            if texto != (solicitud.observaciones_texto or ""):
                cambios.append("Observaciones actualizadas")
            solicitud.observaciones_texto = texto
            solicitud.observaciones = html or (f"<p>{escape(texto)}</p>" if texto else "")

        if es_servicio and descripcion_servicio_texto is not None:
            texto = descripcion_servicio_texto.strip()
            html = html_sin_data_uri((descripcion_servicio or "").strip())
            if texto != (solicitud.descripcion_servicio_texto or ""):
                cambios.append("Descripción del servicio actualizada")
            solicitud.descripcion_servicio_texto = texto
            solicitud.descripcion_servicio = html or (f"<p>{escape(texto)}</p>" if texto else "")

        if es_servicio and proveedor_sugerido is not None:
            nuevo = proveedor_sugerido.strip()
            if nuevo != (solicitud.proveedor_sugerido or ""):
                cambios.append("Proveedor sugerido actualizado")
            solicitud.proveedor_sugerido = nuevo

        productos_nuevos: list[SolicitudGestionProducto] | None = None
        if not es_servicio and productos_json is not None:
            productos_nuevos = _parse_productos(productos_json)
            cambio_items = self._resumir_cambio_productos(
                solicitud.productos, productos_nuevos
            )
            if cambio_items:
                cambios.extend(cambio_items)

        if not cambios:
            raise ValueError("No hay cambios para guardar.")

        self._solicitudes.update(solicitud)
        if productos_nuevos is not None:
            self._solicitudes.reemplazar_productos(solicitud_id, productos_nuevos)

        detalle = "; ".join(cambios)
        usuario = (actor.username or actor.nombre or "el solicitante").strip()
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.SOLICITUD,
            usuario_id=actor.id,
            comentario=f"Solicitud editada por {usuario}. Cambios: {detalle}",
        )

        refreshed = self._solicitudes.get_by_id(solicitud_id)
        return refreshed or solicitud

    @staticmethod
    def _resumir_cambio_productos(
        anteriores: list[SolicitudGestionProducto],
        nuevos: list[SolicitudGestionProducto],
    ) -> list[str]:
        """Describe altas, bajas y modificaciones de ítems por posición/descripción."""
        def clave(p: SolicitudGestionProducto) -> tuple:
            return (
                (p.descripcion or "").strip().lower(),
                (p.unidad or "").strip().lower(),
                str(p.cantidad),
                (p.centro_costo or "").strip().lower(),
                (p.codigo_siimed or "").strip().lower(),
            )

        set_ant = [clave(p) for p in anteriores]
        set_new = [clave(p) for p in nuevos]
        if set_ant == set_new:
            return []

        cambios: list[str] = []
        descr_ant = {(p.descripcion or "").strip().lower() for p in anteriores}
        descr_new = {(p.descripcion or "").strip().lower() for p in nuevos}

        agregados = [
            p for p in nuevos if (p.descripcion or "").strip().lower() not in descr_ant
        ]
        quitados = [
            p for p in anteriores if (p.descripcion or "").strip().lower() not in descr_new
        ]
        for p in agregados:
            cambios.append(
                f"Ítem agregado: «{p.descripcion}» ({_fmt_cantidad(p.cantidad)} {p.unidad})"
            )
        for p in quitados:
            cambios.append(f"Ítem eliminado: «{p.descripcion}»")

        # Modificaciones de cantidad/unidad sobre ítems que siguen (misma descripción).
        por_desc_ant = {(p.descripcion or "").strip().lower(): p for p in anteriores}
        for p in nuevos:
            d = (p.descripcion or "").strip().lower()
            prev = por_desc_ant.get(d)
            if prev is None:
                continue
            if prev.cantidad != p.cantidad:
                cambios.append(
                    f"«{p.descripcion}»: cantidad "
                    f"{_fmt_cantidad(prev.cantidad)} → {_fmt_cantidad(p.cantidad)}"
                )
            if (prev.unidad or "").strip().lower() != (p.unidad or "").strip().lower():
                cambios.append(f"«{p.descripcion}»: unidad {prev.unidad} → {p.unidad}")

        if not cambios:
            cambios.append("Ítems actualizados")
        return cambios
