"""Repositorio SQLAlchemy para solicitudes de gestión."""

from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, aliased, selectinload

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
    SolicitudGestionHistorialEstado,
    SolicitudGestionObservacion,
    SolicitudGestionProducto,
    construir_codigo_solicitud,
)
from app.domain.value_objects.estado_aprobacion_producto import (
    normalizar_estado_aprobacion_producto,
)
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion
from app.infrastructure.database.models import (
    SolicitudGestionArchivoModel,
    SolicitudGestionHistorialEstadoModel,
    SolicitudGestionModel,
    SolicitudGestionObservacionModel,
    SolicitudGestionProductoModel,
    UserModel,
)


class SqlAlchemySolicitudGestionRepository(SolicitudGestionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @classmethod
    def _historial_to_entity(
        cls, model: SolicitudGestionHistorialEstadoModel, username: str = ""
    ) -> SolicitudGestionHistorialEstado:
        return SolicitudGestionHistorialEstado(
            id=model.id,
            solicitud_id=model.solicitud_id,
            etapa=normalizar_estado(model.etapa),
            usuario_id=model.usuario_id,
            usuario_username=username,
            comentario=model.comentario or "",
            created_at=model.created_at,
        )

    @classmethod
    def _archivo_to_entity(cls, model: SolicitudGestionArchivoModel) -> SolicitudGestionArchivo:
        return SolicitudGestionArchivo(
            id=model.id,
            solicitud_id=model.solicitud_id,
            observacion_id=getattr(model, "observacion_id", None),
            nombre_original=model.nombre_original,
            ruta_almacenamiento=model.ruta_almacenamiento,
            mime_type=model.mime_type,
            tamano_bytes=model.tamano_bytes,
            categoria=getattr(model, "categoria", None) or "solicitud",
            subido_por_id=model.subido_por_id,
            created_at=model.created_at,
        )

    @classmethod
    def _observacion_to_entity(cls, model: SolicitudGestionObservacionModel) -> SolicitudGestionObservacion:
        return SolicitudGestionObservacion(
            id=model.id,
            solicitud_id=model.solicitud_id,
            usuario_id=model.usuario_id,
            autor_nombre=model.autor_nombre,
            autor_rol=model.autor_rol,
            contenido=model.contenido,
            contenido_texto=model.contenido_texto or "",
            created_at=model.created_at,
            archivos=[cls._archivo_to_entity(a) for a in (model.archivos or [])],
        )

    @classmethod
    def _to_entity(
        cls,
        model: SolicitudGestionModel,
        creado_por_username: str = "",
        gestor_username: str = "",
        gestor_anticipo_username: str = "",
    ) -> SolicitudGestion:
        return SolicitudGestion(
            id=model.id,
            codigo=model.codigo,
            tipo=TipoSolicitudGestion(model.tipo),
            titulo=model.titulo,
            presupuestado=model.presupuestado,
            centro_costo_area=model.centro_costo_area,
            lider_area_id=model.lider_area_id,
            lider_area_label=model.lider_area_label,
            lider_segunda_aprobacion_id=getattr(model, "lider_segunda_aprobacion_id", "") or "",
            lider_segunda_aprobacion_label=getattr(model, "lider_segunda_aprobacion_label", "")
            or "",
            observaciones=model.observaciones,
            observaciones_texto=model.observaciones_texto,
            observaciones_gestion=getattr(model, "observaciones_gestion", "") or "",
            justificacion_cotizaciones=getattr(model, "justificacion_cotizaciones", "") or "",
            numero_tramite_oc=getattr(model, "numero_tramite_oc", "") or "",
            valor_tramite_oc=getattr(model, "valor_tramite_oc", None),
            requiere_anticipo=bool(getattr(model, "requiere_anticipo", False)),
            porcentaje_anticipo=getattr(model, "porcentaje_anticipo", None),
            lider_anticipo_id=getattr(model, "lider_anticipo_id", "") or "",
            lider_anticipo_label=getattr(model, "lider_anticipo_label", "") or "",
            monto_anticipo=getattr(model, "monto_anticipo", None),
            observaciones_anticipo=getattr(model, "observaciones_anticipo", "") or "",
            gestor_anticipo_id=getattr(model, "gestor_anticipo_id", None),
            gestor_anticipo_username=gestor_anticipo_username,
            gestor_id=getattr(model, "gestor_id", None),
            gestor_username=gestor_username,
            estado=normalizar_estado(model.estado),
            creado_por_id=model.creado_por_id,
            creado_por_username=creado_por_username,
            creado_por_email=getattr(model, "creado_por_email", "") or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
            productos=[
                SolicitudGestionProducto(
                    id=p.id,
                    solicitud_id=p.solicitud_id,
                    codigo_siimed=p.codigo_siimed,
                    unidad=p.unidad,
                    descripcion=p.descripcion,
                    centro_costo=p.centro_costo,
                    cantidad=getattr(p, "cantidad", None) or Decimal("1"),
                    cantidad_recibida=getattr(p, "cantidad_recibida", None) or Decimal("0"),
                    cantidad_entregada=getattr(p, "cantidad_entregada", None) or Decimal("0"),
                    estado_aprobacion=normalizar_estado_aprobacion_producto(
                        getattr(p, "estado_aprobacion", None)
                    ),
                    numero_tramite_oc=getattr(p, "numero_tramite_oc", "") or "",
                    valor_tramite_oc=getattr(p, "valor_tramite_oc", None),
                )
                for p in model.productos
            ],
            archivos=[
                cls._archivo_to_entity(a) for a in model.archivos
            ],
            observaciones_trazabilidad=[
                cls._observacion_to_entity(o) for o in (model.observaciones_trazabilidad or [])
            ],
        )

    def create(self, solicitud: SolicitudGestion) -> SolicitudGestion:
        etapa_inicial = normalizar_estado(solicitud.estado)
        model = SolicitudGestionModel(
            codigo="PENDING",
            tipo=solicitud.tipo.value,
            titulo=solicitud.titulo,
            presupuestado=solicitud.presupuestado,
            centro_costo_area=solicitud.centro_costo_area,
            lider_area_id=solicitud.lider_area_id,
            lider_area_label=solicitud.lider_area_label,
            observaciones=solicitud.observaciones,
            observaciones_texto=solicitud.observaciones_texto,
            estado=etapa_inicial.value,
            creado_por_id=solicitud.creado_por_id,
            creado_por_email=(solicitud.creado_por_email or "").strip(),
        )
        self._db.add(model)
        self._db.flush()
        model.codigo = construir_codigo_solicitud(model.id)

        for producto in solicitud.productos:
            self._db.add(
                SolicitudGestionProductoModel(
                    solicitud_id=model.id,
                    codigo_siimed=producto.codigo_siimed,
                    unidad=producto.unidad,
                    descripcion=producto.descripcion,
                    centro_costo=producto.centro_costo,
                    cantidad=producto.cantidad,
                    cantidad_entregada=producto.cantidad_entregada,
                    estado_aprobacion=producto.estado_aprobacion.value,
                )
            )

        for archivo in solicitud.archivos:
            self._db.add(
                SolicitudGestionArchivoModel(
                    solicitud_id=model.id,
                    nombre_original=archivo.nombre_original,
                    ruta_almacenamiento=archivo.ruta_almacenamiento,
                    mime_type=archivo.mime_type,
                    tamano_bytes=archivo.tamano_bytes,
                    categoria=archivo.categoria or "solicitud",
                    subido_por_id=archivo.subido_por_id,
                )
            )

        self._db.add(
            SolicitudGestionHistorialEstadoModel(
                solicitud_id=model.id,
                etapa=etapa_inicial.value,
                usuario_id=solicitud.creado_por_id,
                comentario="Solicitud registrada",
            )
        )

        self._db.commit()
        created = self.get_by_id(model.id)
        if created is None:
            raise RuntimeError("No se pudo recuperar la solicitud recién creada.")
        return created

    def get_by_id(self, solicitud_id: int) -> Optional[SolicitudGestion]:
        GestorUser = aliased(UserModel)
        GestorAnticipoUser = aliased(UserModel)
        row = (
            self._db.query(
                SolicitudGestionModel,
                UserModel.username,
                GestorUser.username,
                GestorAnticipoUser.username,
            )
            .join(UserModel, SolicitudGestionModel.creado_por_id == UserModel.id)
            .outerjoin(GestorUser, SolicitudGestionModel.gestor_id == GestorUser.id)
            .outerjoin(
                GestorAnticipoUser,
                SolicitudGestionModel.gestor_anticipo_id == GestorAnticipoUser.id,
            )
            .options(
                selectinload(SolicitudGestionModel.productos),
                selectinload(SolicitudGestionModel.archivos),
                selectinload(SolicitudGestionModel.observaciones_trazabilidad).selectinload(
                    SolicitudGestionObservacionModel.archivos
                ),
            )
            .filter(SolicitudGestionModel.id == solicitud_id)
            .one_or_none()
        )
        if not row:
            return None
        model, username, gestor_username, gestor_anticipo_username = row
        return self._to_entity(
            model,
            username,
            gestor_username or "",
            gestor_anticipo_username or "",
        )

    def list_all(
        self,
        *,
        creador_id: Optional[int] = None,
        excluir_creador_id: Optional[int] = None,
        gestor_anticipo_id: Optional[int] = None,
        tipo: Optional[TipoSolicitudGestion] = None,
        estados: Optional[list[EstadoSolicitudGestion]] = None,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        q = (
            self._db.query(SolicitudGestionModel, UserModel.username)
            .join(UserModel, SolicitudGestionModel.creado_por_id == UserModel.id)
            .options(
                selectinload(SolicitudGestionModel.productos),
                selectinload(SolicitudGestionModel.archivos),
                selectinload(SolicitudGestionModel.observaciones_trazabilidad).selectinload(
                    SolicitudGestionObservacionModel.archivos
                ),
            )
        )

        if creador_id is not None:
            q = q.filter(SolicitudGestionModel.creado_por_id == creador_id)
        if excluir_creador_id is not None:
            q = q.filter(SolicitudGestionModel.creado_por_id != excluir_creador_id)
        if gestor_anticipo_id is not None:
            q = q.filter(SolicitudGestionModel.gestor_anticipo_id == gestor_anticipo_id)
        if tipo is not None:
            q = q.filter(SolicitudGestionModel.tipo == tipo.value)
        if estados:
            valores: set[str] = set()
            for estado in estados:
                valores.add(estado.value)
                normalizado = normalizar_estado(estado)
                valores.add(normalizado.value)
            q = q.filter(SolicitudGestionModel.estado.in_(list(valores)))
        if query:
            term = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    SolicitudGestionModel.codigo.ilike(term),
                    SolicitudGestionModel.titulo.ilike(term),
                    SolicitudGestionModel.lider_area_label.ilike(term),
                    UserModel.username.ilike(term),
                )
            )

        rows = q.order_by(SolicitudGestionModel.id.desc()).all()
        return [self._to_entity(model, username) for model, username in rows]

    def update(self, solicitud: SolicitudGestion) -> SolicitudGestion:
        if solicitud.id is None:
            raise ValueError("La solicitud debe tener id para actualizarse.")

        model = (
            self._db.query(SolicitudGestionModel)
            .filter(SolicitudGestionModel.id == solicitud.id)
            .one_or_none()
        )
        if model is None:
            raise ValueError(f"No existe la solicitud {solicitud.id}.")

        model.estado = normalizar_estado(solicitud.estado).value
        model.observaciones_texto = solicitud.observaciones_texto
        model.observaciones_gestion = solicitud.observaciones_gestion
        model.justificacion_cotizaciones = solicitud.justificacion_cotizaciones
        model.numero_tramite_oc = solicitud.numero_tramite_oc or ""
        model.valor_tramite_oc = solicitud.valor_tramite_oc
        model.requiere_anticipo = solicitud.requiere_anticipo
        model.porcentaje_anticipo = solicitud.porcentaje_anticipo
        model.lider_anticipo_id = solicitud.lider_anticipo_id or ""
        model.lider_anticipo_label = solicitud.lider_anticipo_label or ""
        model.monto_anticipo = solicitud.monto_anticipo
        model.observaciones_anticipo = solicitud.observaciones_anticipo or ""
        model.gestor_anticipo_id = solicitud.gestor_anticipo_id
        model.gestor_id = solicitud.gestor_id
        model.lider_segunda_aprobacion_id = solicitud.lider_segunda_aprobacion_id
        model.lider_segunda_aprobacion_label = solicitud.lider_segunda_aprobacion_label
        self._db.commit()

        updated = self.get_by_id(solicitud.id)
        if updated is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        return updated

    def registrar_historial(
        self,
        solicitud_id: int,
        etapa: EstadoSolicitudGestion,
        *,
        usuario_id: Optional[int] = None,
        comentario: str = "",
    ) -> SolicitudGestionHistorialEstado:
        etapa_norm = normalizar_estado(etapa)
        model = SolicitudGestionHistorialEstadoModel(
            solicitud_id=solicitud_id,
            etapa=etapa_norm.value,
            usuario_id=usuario_id,
            comentario=comentario or "",
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        username = ""
        if usuario_id:
            user = self._db.query(UserModel.username).filter(UserModel.id == usuario_id).scalar()
            username = user or ""
        return self._historial_to_entity(model, username)

    def add_archivos(
        self,
        solicitud_id: int,
        archivos: list[SolicitudGestionArchivo],
        observacion_id: Optional[int] = None,
    ) -> list[int]:
        created_ids: list[int] = []
        for archivo in archivos:
            model = SolicitudGestionArchivoModel(
                solicitud_id=solicitud_id,
                nombre_original=archivo.nombre_original,
                ruta_almacenamiento=archivo.ruta_almacenamiento,
                mime_type=archivo.mime_type,
                tamano_bytes=archivo.tamano_bytes,
                categoria=archivo.categoria or "solicitud",
                observacion_id=archivo.observacion_id or observacion_id,
                subido_por_id=archivo.subido_por_id,
            )
            self._db.add(model)
            self._db.flush()
            created_ids.append(model.id)
        self._db.commit()
        return created_ids

    def link_archivos_observacion(self, observacion_id: int, archivo_ids: list[int]) -> None:
        if not archivo_ids:
            return
        (
            self._db.query(SolicitudGestionArchivoModel)
            .filter(SolicitudGestionArchivoModel.id.in_(archivo_ids))
            .update(
                {SolicitudGestionArchivoModel.observacion_id: observacion_id},
                synchronize_session=False,
            )
        )
        self._db.commit()

    def count_archivos_categoria(self, solicitud_id: int, categoria: str) -> int:
        return (
            self._db.query(SolicitudGestionArchivoModel)
            .filter(
                SolicitudGestionArchivoModel.solicitud_id == solicitud_id,
                SolicitudGestionArchivoModel.categoria == categoria,
            )
            .count()
        )

    def add_observacion(
        self,
        solicitud_id: int,
        observacion: SolicitudGestionObservacion,
    ) -> SolicitudGestionObservacion:
        model = SolicitudGestionObservacionModel(
            solicitud_id=solicitud_id,
            usuario_id=observacion.usuario_id,
            autor_nombre=observacion.autor_nombre,
            autor_rol=observacion.autor_rol,
            contenido=observacion.contenido,
            contenido_texto=observacion.contenido_texto or "",
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._observacion_to_entity(model)

    def get_observaciones(self, solicitud_id: int) -> list[SolicitudGestionObservacion]:
        rows = (
            self._db.query(SolicitudGestionObservacionModel)
            .filter(SolicitudGestionObservacionModel.solicitud_id == solicitud_id)
            .order_by(SolicitudGestionObservacionModel.created_at.asc())
            .all()
        )
        return [self._observacion_to_entity(row) for row in rows]

    def get_observacion_by_id(self, observacion_id: int) -> Optional[SolicitudGestionObservacion]:
        model = (
            self._db.query(SolicitudGestionObservacionModel)
            .options(selectinload(SolicitudGestionObservacionModel.archivos))
            .filter(SolicitudGestionObservacionModel.id == observacion_id)
            .one_or_none()
        )
        if not model:
            return None
        return self._observacion_to_entity(model)

    def update_observacion_contenido(self, observacion_id: int, contenido: str) -> None:
        model = (
            self._db.query(SolicitudGestionObservacionModel)
            .filter(SolicitudGestionObservacionModel.id == observacion_id)
            .one_or_none()
        )
        if model is None:
            return
        model.contenido = contenido
        self._db.commit()

    def update_productos_estado_aprobacion(
        self,
        solicitud_id: int,
        estados_por_id: dict[int, str],
    ) -> None:
        if not estados_por_id:
            return
        rows = (
            self._db.query(SolicitudGestionProductoModel)
            .filter(SolicitudGestionProductoModel.solicitud_id == solicitud_id)
            .all()
        )
        for row in rows:
            if row.id in estados_por_id:
                row.estado_aprobacion = estados_por_id[row.id]
        self._db.commit()
        self._db.expire_all()

    def update_productos_cantidades(
        self,
        solicitud_id: int,
        cantidades_por_id: dict[int, Decimal],
    ) -> None:
        if not cantidades_por_id:
            return
        rows = (
            self._db.query(SolicitudGestionProductoModel)
            .filter(SolicitudGestionProductoModel.solicitud_id == solicitud_id)
            .all()
        )
        for row in rows:
            if row.id in cantidades_por_id:
                row.cantidad = cantidades_por_id[row.id]
        self._db.commit()
        self._db.expire_all()

    def update_tramite_oc(
        self,
        solicitud_id: int,
        *,
        numero_tramite_oc: Optional[str] = None,
        valor_tramite_oc: Optional[Decimal] = None,
        numeros_por_producto: Optional[dict[int, str]] = None,
        valores_por_producto: Optional[dict[int, Decimal]] = None,
    ) -> None:
        if numero_tramite_oc is not None:
            model = (
                self._db.query(SolicitudGestionModel)
                .filter(SolicitudGestionModel.id == solicitud_id)
                .one_or_none()
            )
            if model is None:
                raise ValueError(f"No existe la solicitud {solicitud_id}.")
            model.numero_tramite_oc = (numero_tramite_oc or "").strip()
            model.valor_tramite_oc = valor_tramite_oc

        if numeros_por_producto or valores_por_producto:
            rows = (
                self._db.query(SolicitudGestionProductoModel)
                .filter(SolicitudGestionProductoModel.solicitud_id == solicitud_id)
                .all()
            )
            for row in rows:
                if numeros_por_producto and row.id in numeros_por_producto:
                    row.numero_tramite_oc = (numeros_por_producto[row.id] or "").strip()
                if valores_por_producto and row.id in valores_por_producto:
                    row.valor_tramite_oc = valores_por_producto[row.id]

        self._db.commit()
        self._db.expire_all()

    def update_productos_cantidad_entregada(
        self,
        solicitud_id: int,
        cantidades_por_id: dict[int, Decimal],
    ) -> None:
        if not cantidades_por_id:
            return
        rows = (
            self._db.query(SolicitudGestionProductoModel)
            .filter(SolicitudGestionProductoModel.solicitud_id == solicitud_id)
            .all()
        )
        for row in rows:
            if row.id in cantidades_por_id:
                row.cantidad_entregada = cantidades_por_id[row.id]
        self._db.commit()
        self._db.expire_all()

    def update_productos_cantidad_recibida(
        self,
        solicitud_id: int,
        cantidades_por_id: dict[int, Decimal],
    ) -> None:
        if not cantidades_por_id:
            return
        rows = (
            self._db.query(SolicitudGestionProductoModel)
            .filter(SolicitudGestionProductoModel.solicitud_id == solicitud_id)
            .all()
        )
        for row in rows:
            if row.id in cantidades_por_id:
                row.cantidad_recibida = cantidades_por_id[row.id]
        self._db.commit()
        self._db.expire_all()

    def get_historial(self, solicitud_id: int) -> list[SolicitudGestionHistorialEstado]:
        rows = (
            self._db.query(SolicitudGestionHistorialEstadoModel, UserModel.username)
            .outerjoin(UserModel, SolicitudGestionHistorialEstadoModel.usuario_id == UserModel.id)
            .filter(SolicitudGestionHistorialEstadoModel.solicitud_id == solicitud_id)
            .order_by(SolicitudGestionHistorialEstadoModel.created_at.asc())
            .all()
        )
        return [self._historial_to_entity(model, username or "") for model, username in rows]
