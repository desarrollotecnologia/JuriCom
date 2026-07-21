"""Implementación de ContratoRepository sobre SQLAlchemy + MySQL."""

from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import (
    ArchivoAdjunto,
    Contrato,
    TipoArchivo,
    construir_codigo,
    normalizar_tipo_codigo,
)
from app.domain.entities.otrosi import Otrosi
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_otrosi import TipoOtrosi
from app.domain.value_objects.unidad_plazo import UnidadPlazo
from app.infrastructure.database.models import (
    ArchivoContratoModel,
    ContratoModel,
    OtrosiContratoModel,
)


class SqlAlchemyContratoRepository(ContratoRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _normalizar_hora(value) -> Optional[time]:
        if value is None or isinstance(value, time):
            return value
        if isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return time(hours, minutes, seconds)
        return value

    @staticmethod
    def _archivo_to_entity(m: ArchivoContratoModel) -> ArchivoAdjunto:
        return ArchivoAdjunto(
            id=m.id,
            contrato_id=m.contrato_id,
            tipo=TipoArchivo(m.tipo),
            nombre_original=m.nombre_original,
            ruta_almacenamiento=m.ruta_almacenamiento,
            mime_type=m.mime_type,
            tamano_bytes=m.tamano_bytes,
            subido_por_id=m.subido_por_id,
            created_at=m.created_at,
        )

    @staticmethod
    def _otrosi_to_entity(m: OtrosiContratoModel) -> Otrosi:
        return Otrosi(
            id=m.id,
            contrato_id=m.contrato_id,
            numero=m.numero,
            tipo=TipoOtrosi(m.tipo),
            descripcion=m.descripcion,
            plazo_adicional_cantidad=m.plazo_adicional_cantidad,
            plazo_adicional_unidad=(
                UnidadPlazo(m.plazo_adicional_unidad)
                if m.plazo_adicional_unidad
                else None
            ),
            valor_adicional=m.valor_adicional,
            nueva_descripcion_servicio=m.nueva_descripcion_servicio,
            archivo_id=m.archivo_id,
            estado_aprobacion=EstadoAprobacion(m.estado_aprobacion),
            aprobado_lider_at=m.aprobado_lider_at,
            aprobado_gerencia_at=m.aprobado_gerencia_at,
            creado_por_id=m.creado_por_id,
            created_at=m.created_at,
        )

    @classmethod
    def _to_entity(cls, model: ContratoModel) -> Contrato:
        return Contrato(
            id=model.id,
            codigo=model.codigo,
            tipo_codigo=getattr(model, "tipo_codigo", "") or "C",
            solicitud_gestion_id=getattr(model, "solicitud_gestion_id", None),
            solicitud_gestion_codigo=getattr(model, "solicitud_gestion_codigo", "") or "",
            compania=model.compania,
            proveedor_contratista=model.proveedor_contratista,
            nit_proveedor=model.nit_proveedor,
            descripcion_servicio=model.descripcion_servicio,
            obligaciones_colbeef=model.obligaciones_colbeef,
            obligaciones_proveedor=model.obligaciones_proveedor,
            valor=model.valor,
            moneda=Moneda(model.moneda),
            plazo_cantidad=model.plazo_cantidad,
            plazo_unidad=UnidadPlazo(model.plazo_unidad),
            renovacion_automatica=model.renovacion_automatica,
            condiciones_recibido_satisfactorio=model.condiciones_recibido_satisfactorio,
            requiere_poliza=model.requiere_poliza,
            correo_lider_proceso=model.correo_lider_proceso,
            correo_gerencia=model.correo_gerencia,
            estado_aprobacion=EstadoAprobacion(model.estado_aprobacion),
            estado=EstadoContrato(model.estado),
            fecha_inicio=model.fecha_inicio,
            fecha_fin=model.fecha_fin,
            fecha_proxima_notificacion=model.fecha_proxima_notificacion,
            hora_proxima_notificacion=cls._normalizar_hora(
                getattr(model, "hora_proxima_notificacion", None)
            ),
            fecha_ultima_notificacion_vencimiento=getattr(
                model, "fecha_ultima_notificacion_vencimiento", None
            ),
            aprobado_lider_at=model.aprobado_lider_at,
            aprobado_gerencia_at=model.aprobado_gerencia_at,
            eliminado_at=getattr(model, "eliminado_at", None),
            eliminado_por_id=getattr(model, "eliminado_por_id", None),
            eliminado_observacion=getattr(model, "eliminado_observacion", "") or "",
            creado_por_id=model.creado_por_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            archivos=[cls._archivo_to_entity(a) for a in model.archivos],
            otrosies=[cls._otrosi_to_entity(o) for o in model.otrosies],
        )

    def create(self, contrato: Contrato) -> Contrato:
        tipo_codigo = normalizar_tipo_codigo(contrato.tipo_codigo)
        model = ContratoModel(
            codigo="PENDIENTE",  # placeholder; lo asignamos tras conocer el id
            tipo_codigo=tipo_codigo,
            solicitud_gestion_id=contrato.solicitud_gestion_id,
            solicitud_gestion_codigo=contrato.solicitud_gestion_codigo or "",
            compania=contrato.compania,
            proveedor_contratista=contrato.proveedor_contratista,
            nit_proveedor=contrato.nit_proveedor,
            descripcion_servicio=contrato.descripcion_servicio,
            obligaciones_colbeef=contrato.obligaciones_colbeef,
            obligaciones_proveedor=contrato.obligaciones_proveedor,
            valor=contrato.valor,
            moneda=contrato.moneda.value,
            plazo_cantidad=contrato.plazo_cantidad,
            plazo_unidad=contrato.plazo_unidad.value,
            renovacion_automatica=contrato.renovacion_automatica,
            condiciones_recibido_satisfactorio=contrato.condiciones_recibido_satisfactorio,
            requiere_poliza=contrato.requiere_poliza,
            correo_lider_proceso=contrato.correo_lider_proceso,
            correo_gerencia=contrato.correo_gerencia,
            estado_aprobacion=contrato.estado_aprobacion.value,
            estado=contrato.estado.value,
            fecha_inicio=contrato.fecha_inicio,
            fecha_fin=contrato.fecha_fin,
            fecha_proxima_notificacion=contrato.fecha_proxima_notificacion,
            hora_proxima_notificacion=contrato.hora_proxima_notificacion,
            fecha_ultima_notificacion_vencimiento=contrato.fecha_ultima_notificacion_vencimiento,
            aprobado_lider_at=contrato.aprobado_lider_at,
            aprobado_gerencia_at=contrato.aprobado_gerencia_at,
            creado_por_id=contrato.creado_por_id,
            archivos=[
                ArchivoContratoModel(
                    tipo=a.tipo.value,
                    nombre_original=a.nombre_original,
                    ruta_almacenamiento=a.ruta_almacenamiento,
                    mime_type=a.mime_type,
                    tamano_bytes=a.tamano_bytes,
                    subido_por_id=a.subido_por_id or contrato.creado_por_id,
                )
                for a in contrato.archivos
            ],
        )
        self._db.add(model)
        self._db.flush()
        model.codigo = construir_codigo(
            self._siguiente_consecutivo_codigo(tipo_codigo),
            tipo_codigo,
        )
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def _siguiente_consecutivo_codigo(self, tipo_codigo: str) -> int:
        prefix = normalizar_tipo_codigo(tipo_codigo)
        codigos = (
            self._db.query(ContratoModel.codigo)
            .filter(ContratoModel.codigo.like(f"{prefix}-%"))
            .all()
        )
        mayor = 0
        for (codigo,) in codigos:
            parte = (codigo or "").split("-", 1)
            if len(parte) != 2 or parte[0] != prefix:
                continue
            try:
                mayor = max(mayor, int(parte[1]))
            except ValueError:
                continue
        return mayor + 1

    def update(self, contrato: Contrato) -> Contrato:
        if contrato.id is None:
            raise ValueError("No se puede actualizar un contrato sin id.")
        model = (
            self._db.query(ContratoModel)
            .options(
                selectinload(ContratoModel.archivos),
                selectinload(ContratoModel.otrosies),
            )
            .filter(ContratoModel.id == contrato.id)
            .one_or_none()
        )
        if model is None:
            raise ValueError(f"Contrato {contrato.id} no existe en BD.")

        # Campos que pueden cambiar (estado, aprobación, vigencia y otrosíes).
        model.estado = contrato.estado.value
        model.estado_aprobacion = contrato.estado_aprobacion.value
        model.aprobado_lider_at = contrato.aprobado_lider_at
        model.aprobado_gerencia_at = contrato.aprobado_gerencia_at
        model.fecha_inicio = contrato.fecha_inicio
        model.fecha_fin = contrato.fecha_fin
        model.fecha_proxima_notificacion = contrato.fecha_proxima_notificacion
        model.hora_proxima_notificacion = contrato.hora_proxima_notificacion
        model.fecha_ultima_notificacion_vencimiento = (
            contrato.fecha_ultima_notificacion_vencimiento
        )
        model.valor = contrato.valor
        model.plazo_cantidad = contrato.plazo_cantidad
        model.plazo_unidad = contrato.plazo_unidad.value
        model.descripcion_servicio = contrato.descripcion_servicio
        model.proveedor_contratista = contrato.proveedor_contratista
        model.nit_proveedor = contrato.nit_proveedor
        model.obligaciones_colbeef = contrato.obligaciones_colbeef
        model.obligaciones_proveedor = contrato.obligaciones_proveedor
        model.moneda = contrato.moneda.value
        model.renovacion_automatica = contrato.renovacion_automatica
        model.condiciones_recibido_satisfactorio = contrato.condiciones_recibido_satisfactorio
        model.requiere_poliza = contrato.requiere_poliza
        model.correo_lider_proceso = contrato.correo_lider_proceso
        model.correo_gerencia = contrato.correo_gerencia

        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def delete(
        self,
        contrato_id: int,
        eliminado_por_id: Optional[int] = None,
        observacion: str = "",
    ) -> bool:
        model = (
            self._db.query(ContratoModel)
            .filter(ContratoModel.id == contrato_id)
            .one_or_none()
        )
        if model is None:
            return False
        model.eliminado_at = datetime.now()
        model.eliminado_por_id = eliminado_por_id
        model.eliminado_observacion = observacion
        self._db.commit()
        return True

    def add_otrosi(self, otrosi: Otrosi) -> Otrosi:
        model = OtrosiContratoModel(
            contrato_id=otrosi.contrato_id,
            numero=otrosi.numero,
            tipo=otrosi.tipo.value,
            descripcion=otrosi.descripcion,
            plazo_adicional_cantidad=otrosi.plazo_adicional_cantidad,
            plazo_adicional_unidad=(
                otrosi.plazo_adicional_unidad.value
                if otrosi.plazo_adicional_unidad
                else None
            ),
            valor_adicional=otrosi.valor_adicional,
            nueva_descripcion_servicio=otrosi.nueva_descripcion_servicio,
            archivo_id=otrosi.archivo_id,
            estado_aprobacion=otrosi.estado_aprobacion.value,
            aprobado_lider_at=otrosi.aprobado_lider_at,
            aprobado_gerencia_at=otrosi.aprobado_gerencia_at,
            creado_por_id=otrosi.creado_por_id,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._otrosi_to_entity(model)

    def update_otrosi(self, otrosi: Otrosi) -> Otrosi:
        if otrosi.id is None:
            raise ValueError("No se puede actualizar un otrosí sin id.")
        model = (
            self._db.query(OtrosiContratoModel)
            .filter(OtrosiContratoModel.id == otrosi.id)
            .one_or_none()
        )
        if model is None:
            raise ValueError(f"Otrosí {otrosi.id} no existe en BD.")

        model.tipo = otrosi.tipo.value
        model.descripcion = otrosi.descripcion
        model.plazo_adicional_cantidad = otrosi.plazo_adicional_cantidad
        model.plazo_adicional_unidad = (
            otrosi.plazo_adicional_unidad.value
            if otrosi.plazo_adicional_unidad
            else None
        )
        model.valor_adicional = otrosi.valor_adicional
        model.nueva_descripcion_servicio = otrosi.nueva_descripcion_servicio
        model.archivo_id = otrosi.archivo_id
        model.estado_aprobacion = otrosi.estado_aprobacion.value
        model.aprobado_lider_at = otrosi.aprobado_lider_at
        model.aprobado_gerencia_at = otrosi.aprobado_gerencia_at
        self._db.commit()
        self._db.refresh(model)
        return self._otrosi_to_entity(model)

    def get_otrosi(self, otrosi_id: int) -> Optional[Otrosi]:
        model = (
            self._db.query(OtrosiContratoModel)
            .filter(OtrosiContratoModel.id == otrosi_id)
            .one_or_none()
        )
        return self._otrosi_to_entity(model) if model else None

    def list_otrosies_by_estado_aprobacion(
        self, estado: EstadoAprobacion
    ) -> list[tuple[Contrato, Otrosi]]:
        models = (
            self._db.query(OtrosiContratoModel)
            .join(ContratoModel)
            .options(selectinload(OtrosiContratoModel.contrato))
            .filter(OtrosiContratoModel.estado_aprobacion == estado.value)
            .filter(ContratoModel.eliminado_at.is_(None))
            .order_by(OtrosiContratoModel.id.desc())
            .all()
        )
        return [
            (self._to_entity(m.contrato), self._otrosi_to_entity(m))
            for m in models
        ]

    def add_archivo(self, archivo: ArchivoAdjunto) -> ArchivoAdjunto:
        if archivo.contrato_id is None:
            raise ValueError("El archivo debe tener contrato_id asignado.")
        model = ArchivoContratoModel(
            contrato_id=archivo.contrato_id,
            tipo=archivo.tipo.value,
            nombre_original=archivo.nombre_original,
            ruta_almacenamiento=archivo.ruta_almacenamiento,
            mime_type=archivo.mime_type,
            tamano_bytes=archivo.tamano_bytes,
            subido_por_id=archivo.subido_por_id,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._archivo_to_entity(model)

    def _query_base(self):
        return self._db.query(ContratoModel).options(
            selectinload(ContratoModel.archivos),
            selectinload(ContratoModel.otrosies),
        )

    def get_by_id(self, contrato_id: int) -> Optional[Contrato]:
        model = self._query_base().filter(ContratoModel.id == contrato_id).one_or_none()
        return self._to_entity(model) if model else None

    def get_by_codigo(self, codigo: str) -> Optional[Contrato]:
        model = self._query_base().filter(ContratoModel.codigo == codigo).one_or_none()
        return self._to_entity(model) if model else None

    def list_all(self, incluir_eliminados: bool = False) -> list[Contrato]:
        q = self._query_base()
        if incluir_eliminados:
            q = q.filter(ContratoModel.eliminado_at.isnot(None))
        else:
            q = q.filter(ContratoModel.eliminado_at.is_(None))
        models = q.order_by(ContratoModel.id.desc()).all()
        return [self._to_entity(m) for m in models]

    def list_by_creador(self, user_id: int, incluir_eliminados: bool = False) -> list[Contrato]:
        q = self._query_base().filter(ContratoModel.creado_por_id == user_id)
        if incluir_eliminados:
            q = q.filter(ContratoModel.eliminado_at.isnot(None))
        else:
            q = q.filter(ContratoModel.eliminado_at.is_(None))
        models = q.order_by(ContratoModel.id.desc()).all()
        return [self._to_entity(m) for m in models]

    def user_has_related_records(self, user_id: int) -> bool:
        contrato = (
            self._db.query(ContratoModel.id)
            .filter(ContratoModel.creado_por_id == user_id)
            .limit(1)
            .one_or_none()
        )
        if contrato is not None:
            return True
        otrosi = (
            self._db.query(OtrosiContratoModel.id)
            .filter(OtrosiContratoModel.creado_por_id == user_id)
            .limit(1)
            .one_or_none()
        )
        return otrosi is not None

    def list_by_estado(self, estado: EstadoContrato) -> list[Contrato]:
        models = (
            self._query_base()
            .filter(ContratoModel.estado == estado.value)
            .filter(ContratoModel.eliminado_at.is_(None))
            .order_by(ContratoModel.id.desc())
            .all()
        )
        return [self._to_entity(m) for m in models]

    def search(
        self,
        *,
        query: Optional[str] = None,
        estado: Optional[EstadoContrato] = None,
        creador_id: Optional[int] = None,
        solo_aprobados: bool = False,
        incluir_eliminados: bool = False,
    ) -> list[Contrato]:
        q = self._query_base()
        if incluir_eliminados:
            q = q.filter(ContratoModel.eliminado_at.isnot(None))
        else:
            q = q.filter(ContratoModel.eliminado_at.is_(None))

        if query:
            patron = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    ContratoModel.codigo.like(patron),
                    ContratoModel.proveedor_contratista.like(patron),
                    ContratoModel.nit_proveedor.like(patron),
                )
            )
        if estado is not None:
            q = q.filter(ContratoModel.estado == estado.value)
        if creador_id is not None:
            q = q.filter(ContratoModel.creado_por_id == creador_id)
        if solo_aprobados:
            q = q.filter(ContratoModel.estado_aprobacion == EstadoAprobacion.APROBADO.value)

        models = q.order_by(ContratoModel.id.desc()).all()
        return [self._to_entity(m) for m in models]
