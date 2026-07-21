"""Modelos SQLAlchemy (capa infrastructure).

Estos modelos son SÓLO de persistencia. La lógica de negocio vive en las
entidades del dominio (`app.domain.entities`). Los repositorios se
encargan de traducir entre estos modelos y las entidades.
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.session import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    lider_catalog_id: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class ContratoModel(Base):
    __tablename__ = "contratos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    tipo_codigo: Mapped[str] = mapped_column(String(10), nullable=False, default="C")
    solicitud_gestion_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    solicitud_gestion_codigo: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    compania: Mapped[str] = mapped_column(String(150), nullable=False, default="Colbeef")
    proveedor_contratista: Mapped[str] = mapped_column(String(255), nullable=False)
    nit_proveedor: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    descripcion_servicio: Mapped[str] = mapped_column(Text, nullable=False)
    obligaciones_colbeef: Mapped[str] = mapped_column(Text, nullable=False)
    obligaciones_proveedor: Mapped[str] = mapped_column(Text, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False)
    plazo_cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    plazo_unidad: Mapped[str] = mapped_column(String(10), nullable=False)
    renovacion_automatica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    condiciones_recibido_satisfactorio: Mapped[str] = mapped_column(Text, nullable=False)
    requiere_poliza: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    correo_lider_proceso: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    correo_gerencia: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    estado_aprobacion: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pendiente_lider", index=True
    )
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="en_proceso", index=True
    )
    fecha_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_proxima_notificacion: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hora_proxima_notificacion: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    fecha_ultima_notificacion_vencimiento: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    aprobado_lider_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    aprobado_gerencia_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    eliminado_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    eliminado_por_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    eliminado_observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creado_por_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    archivos: Mapped[list["ArchivoContratoModel"]] = relationship(
        "ArchivoContratoModel",
        back_populates="contrato",
        cascade="all, delete-orphan",
    )

    otrosies: Mapped[list["OtrosiContratoModel"]] = relationship(
        "OtrosiContratoModel",
        back_populates="contrato",
        cascade="all, delete-orphan",
        order_by="OtrosiContratoModel.numero.asc()",
    )


class ArchivoContratoModel(Base):
    __tablename__ = "archivos_contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contrato_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_almacenamiento: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subido_por_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    contrato: Mapped["ContratoModel"] = relationship(
        "ContratoModel", back_populates="archivos"
    )


class OtrosiContratoModel(Base):
    __tablename__ = "otrosies_contrato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contrato_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3... por contrato
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # prorroga | adicion | modificacion | otro
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)

    # Campos específicos del cambio (según tipo)
    plazo_adicional_cantidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    plazo_adicional_unidad: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    valor_adicional: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    nueva_descripcion_servicio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # PDF del otrosí firmado (opcional)
    archivo_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("archivos_contrato.id", ondelete="SET NULL"), nullable=True
    )
    estado_aprobacion: Mapped[str] = mapped_column(
        String(30), nullable=False, default="aprobado", index=True
    )
    aprobado_lider_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    aprobado_gerencia_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    creado_por_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    contrato: Mapped["ContratoModel"] = relationship(
        "ContratoModel", back_populates="otrosies"
    )


class SolicitudGestionModel(Base):
    __tablename__ = "solicitudes_gestion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    numero_consecutivo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    titulo: Mapped[str] = mapped_column(String(500), nullable=False)
    presupuestado: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    centro_costo_area: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    lider_area_id: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    lider_area_label: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    observaciones: Mapped[str] = mapped_column(Text, nullable=False, default="")
    observaciones_texto: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requiere_visita: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    servicio_programado: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fecha_servicio_programado: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    descripcion_servicio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    descripcion_servicio_texto: Mapped[str] = mapped_column(Text, nullable=False, default="")
    proveedor_sugerido: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    observaciones_gestion: Mapped[str] = mapped_column(Text, nullable=False, default="")
    justificacion_cotizaciones: Mapped[str] = mapped_column(Text, nullable=False, default="")
    numero_tramite_oc: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    valor_tramite_oc: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    gestor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lider_segunda_aprobacion_id: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    lider_segunda_aprobacion_label: Mapped[str] = mapped_column(
        String(500), nullable=False, default=""
    )
    requiere_anticipo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    porcentaje_anticipo: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    lider_anticipo_id: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    lider_anticipo_label: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    monto_anticipo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    observaciones_anticipo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    gestor_anticipo_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    anticipo_gestionado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clasificacion_documento_servicio: Mapped[str] = mapped_column(
        String(40), nullable=False, default=""
    )
    gestion_valor_registrada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contrato_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("contratos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contrato_codigo: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    factura_registrada_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    factura_registrada_por_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    estado: Mapped[str] = mapped_column(
        String(30), nullable=False, default="solicitud", index=True
    )
    creado_por_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    creado_por_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    productos: Mapped[list["SolicitudGestionProductoModel"]] = relationship(
        "SolicitudGestionProductoModel",
        back_populates="solicitud",
        cascade="all, delete-orphan",
    )
    archivos: Mapped[list["SolicitudGestionArchivoModel"]] = relationship(
        "SolicitudGestionArchivoModel",
        back_populates="solicitud",
        cascade="all, delete-orphan",
    )
    visitas_programadas: Mapped[list["SolicitudGestionVisitaProgramadaModel"]] = relationship(
        "SolicitudGestionVisitaProgramadaModel",
        back_populates="solicitud",
        cascade="all, delete-orphan",
        order_by="SolicitudGestionVisitaProgramadaModel.id",
    )
    observaciones_trazabilidad: Mapped[list["SolicitudGestionObservacionModel"]] = relationship(
        "SolicitudGestionObservacionModel",
        back_populates="solicitud",
        cascade="all, delete-orphan",
        order_by="SolicitudGestionObservacionModel.created_at",
    )
    historial_estados: Mapped[list["SolicitudGestionHistorialEstadoModel"]] = relationship(
        "SolicitudGestionHistorialEstadoModel",
        back_populates="solicitud",
        cascade="all, delete-orphan",
        order_by="SolicitudGestionHistorialEstadoModel.created_at",
    )


class SolicitudGestionHistorialEstadoModel(Base):
    __tablename__ = "solicitudes_gestion_historial_estados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    etapa: Mapped[str] = mapped_column(String(40), nullable=False)
    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    comentario: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    solicitud: Mapped["SolicitudGestionModel"] = relationship(
        "SolicitudGestionModel", back_populates="historial_estados"
    )
    usuario: Mapped[Optional["UserModel"]] = relationship("UserModel")


class SolicitudGestionProductoModel(Base):
    __tablename__ = "solicitudes_gestion_productos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    codigo_siimed: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    unidad: Mapped[str] = mapped_column(String(20), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    area_consumo: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    centro_costo: Mapped[str] = mapped_column(String(100), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("1")
    )
    cantidad_entregada: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    cantidad_recibida: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    estado_aprobacion: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pendiente"
    )
    numero_tramite_oc: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    valor_tramite_oc: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)

    solicitud: Mapped["SolicitudGestionModel"] = relationship(
        "SolicitudGestionModel", back_populates="productos"
    )


class SolicitudGestionArchivoModel(Base):
    __tablename__ = "solicitudes_gestion_archivos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    ruta_almacenamiento: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tamano_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    categoria: Mapped[str] = mapped_column(String(30), nullable=False, default="solicitud")
    observacion_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion_observaciones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    subido_por_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    solicitud: Mapped["SolicitudGestionModel"] = relationship(
        "SolicitudGestionModel", back_populates="archivos"
    )
    observacion: Mapped[Optional["SolicitudGestionObservacionModel"]] = relationship(
        "SolicitudGestionObservacionModel", back_populates="archivos"
    )


class SolicitudGestionObservacionModel(Base):
    __tablename__ = "solicitudes_gestion_observaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    autor_nombre: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    autor_rol: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    contenido_texto: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    solicitud: Mapped["SolicitudGestionModel"] = relationship(
        "SolicitudGestionModel", back_populates="observaciones_trazabilidad"
    )
    usuario: Mapped[Optional["UserModel"]] = relationship("UserModel")
    archivos: Mapped[list["SolicitudGestionArchivoModel"]] = relationship(
        "SolicitudGestionArchivoModel",
        back_populates="observacion",
        order_by="SolicitudGestionArchivoModel.created_at",
    )


class SolicitudGestionVisitaProgramadaModel(Base):
    __tablename__ = "solicitudes_gestion_visitas_programadas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    solicitud_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("solicitudes_gestion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programador_visita: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    proveedor_visita: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    fecha_visita: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hora_visita: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    solicitud: Mapped["SolicitudGestionModel"] = relationship(
        "SolicitudGestionModel", back_populates="visitas_programadas"
    )
