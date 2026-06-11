"""Entidad Otrosí — modificación a un contrato existente.

Cada otrosí queda registrado en el historial (no se borra/sobrescribe)
y al aplicarse modifica los campos correspondientes del contrato.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.domain.value_objects.tipo_otrosi import TipoOtrosi
from app.domain.value_objects.unidad_plazo import UnidadPlazo
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion


@dataclass
class Otrosi:
    contrato_id: int
    tipo: TipoOtrosi
    descripcion: str  # Motivo / texto del otrosí (siempre obligatorio)
    creado_por_id: int

    # --- Datos específicos según el tipo (todos opcionales) ---
    # PRORROGA: cuánto plazo adicional se otorga
    plazo_adicional_cantidad: Optional[int] = None
    plazo_adicional_unidad: Optional[UnidadPlazo] = None

    # ADICION: cuánto valor adicional se otorga (en la moneda del contrato)
    valor_adicional: Optional[Decimal] = None

    # MODIFICACION: nuevo texto para la descripción del servicio del contrato
    nueva_descripcion_servicio: Optional[str] = None

    # --- Archivo opcional adjunto (PDF del otrosí firmado) ---
    archivo_id: Optional[int] = None  # FK al archivo en archivos_contrato
    estado_aprobacion: EstadoAprobacion = EstadoAprobacion.APROBADO
    aprobado_lider_at: Optional[datetime] = None
    aprobado_gerencia_at: Optional[datetime] = None

    # --- Metadatos ---
    id: Optional[int] = None
    numero: Optional[int] = None  # Número secuencial 1, 2, 3... por contrato
    created_at: Optional[datetime] = None
