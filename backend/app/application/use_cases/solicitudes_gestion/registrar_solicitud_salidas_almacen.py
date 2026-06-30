"""Registra una solicitud de salidas de almacén con ítems y archivos adjuntos."""

import json
from decimal import Decimal, InvalidOperation

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
    SolicitudGestionProducto,
)
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class RegistrarSolicitudSalidasAlmacen:
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
        titulo: str,
        centro_costo_area: str,
        lider_area_id: str,
        lider_area_label: str,
        observaciones: str,
        observaciones_texto: str,
        productos_json: str,
        archivos: list[ArchivoEntradaSolicitud],
    ) -> SolicitudGestion:
        if not (actor.is_compras() or actor.is_admin()):
            raise UnauthorizedError(
                "Sólo Compras o Admin pueden registrar salidas de almacén."
            )

        titulo = (titulo or "").strip()
        if not titulo:
            raise ValueError("El título de la solicitud es obligatorio.")
        if not centro_costo_area:
            raise ValueError("El centro de costo del área solicitante es obligatorio.")
        if not lider_area_id:
            raise ValueError("Debes seleccionar un líder aprobador.")

        try:
            productos_raw = json.loads(productos_json or "[]")
        except json.JSONDecodeError as e:
            raise ValueError("El detalle de la salida no es válido.") from e

        if not isinstance(productos_raw, list) or not productos_raw:
            raise ValueError("Debes agregar al menos un ítem en el detalle de la salida.")

        productos: list[SolicitudGestionProducto] = []
        for i, item in enumerate(productos_raw, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Ítem {i}: formato inválido.")
            descripcion = str(item.get("descripcion") or "").strip()
            if not descripcion:
                raise ValueError(f"Ítem {i}: la descripción es obligatoria.")
            area_consumo = str(item.get("area_consumo") or "").strip()
            if not area_consumo:
                raise ValueError(f"Ítem {i}: el área de consumo es obligatoria.")
            centro = str(item.get("centro_costo") or "").strip()
            if not centro:
                raise ValueError(f"Ítem {i}: el centro de costo es obligatorio.")
            cantidad_raw = item.get("cantidad", 1)
            try:
                cantidad = Decimal(str(cantidad_raw).replace(",", ".").strip() or "1")
            except (InvalidOperation, ValueError) as e:
                raise ValueError(f"Ítem {i}: cantidad inválida.") from e
            if cantidad <= 0:
                raise ValueError(f"Ítem {i}: la cantidad debe ser mayor a cero.")
            productos.append(
                SolicitudGestionProducto(
                    codigo_siimed=str(item.get("codigo_siimed") or "").strip(),
                    unidad="UND",
                    descripcion=descripcion,
                    area_consumo=area_consumo,
                    centro_costo=centro,
                    cantidad=cantidad,
                )
            )

        solicitud = SolicitudGestion(
            tipo=TipoSolicitudGestion.SALIDAS_ALMACEN,
            titulo=titulo,
            presupuestado=False,
            centro_costo_area=centro_costo_area.strip(),
            lider_area_id=str(lider_area_id).strip(),
            lider_area_label=(lider_area_label or "").strip(),
            observaciones=observaciones or "",
            observaciones_texto=(observaciones_texto or "").strip(),
            creado_por_id=actor.id,
            creado_por_email=(actor.email or "").strip(),
            estado=EstadoSolicitudGestion.SOLICITUD,
        )

        for entrada in archivos:
            stored = self._storage.save(
                contenido=entrada.contenido,
                nombre_original=entrada.nombre_original,
                mime_type=entrada.mime_type,
                subcarpeta="solicitudes",
            )
            solicitud.archivos.append(
                SolicitudGestionArchivo(
                    nombre_original=stored.nombre_original,
                    ruta_almacenamiento=stored.ruta,
                    mime_type=stored.mime_type,
                    tamano_bytes=stored.tamano_bytes,
                    subido_por_id=actor.id,
                )
            )

        solicitud.productos = productos
        created = self._solicitudes.create(solicitud)

        tiene_obs = (observaciones_texto or "").strip() or (observaciones or "").strip()
        tiene_archivos = bool(archivos)
        if tiene_obs or tiene_archivos:
            from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
                AgregarObservacionSolicitud,
            )

            obs = AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                created.id,
                contenido=observaciones or "",
                contenido_texto=observaciones_texto or "",
                contexto_rol="solicitante",
            )
            if tiene_archivos:
                refreshed = self._solicitudes.get_by_id(created.id)
                if refreshed:
                    archivo_ids = [
                        a.id
                        for a in refreshed.archivos
                        if a.id and not a.observacion_id and a.categoria == "solicitud"
                    ]
                    self._solicitudes.link_archivos_observacion(obs.id, archivo_ids)

        refreshed = self._solicitudes.get_by_id(created.id)
        return refreshed or created
