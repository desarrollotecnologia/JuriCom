"""Modelos SQLAlchemy (capa infrastructure).

Estos modelos son SÓLO de persistencia. La lógica de negocio vive en las
entidades del dominio (`app.domain.entities`). Los repositorios se
encargan de traducir entre estos modelos y las entidades.
"""

from datetime import date, datetime
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
    aprobado_lider_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    aprobado_gerencia_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
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
