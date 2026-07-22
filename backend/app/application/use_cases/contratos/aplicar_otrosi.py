"""Caso de uso: aplicar un otrosí a un contrato.

Reglas de negocio:
- Jurídica/Admin pueden aplicar otrosíes.
- Compras también puede aplicar otrosíes, pero sólo sobre contratos propios.
- El contrato debe estar en estado ACTIVO (no tiene sentido modificar uno
  finalizado, y los "en_proceso" todavía no se han firmado).
- Cada otrosí queda registrado y APLICA inmediatamente sus cambios sobre
  los campos correspondientes del contrato.

Efectos según el tipo:
- PRORROGA      → suma `plazo_adicional_cantidad` a `plazo_cantidad`
                  (en la misma unidad del contrato).
- ADICION       → suma `valor_adicional` al `valor` del contrato.
- MODIFICACION  → reemplaza `descripcion_servicio` con la nueva.
- OTRO          → sólo deja el registro (no modifica campos del contrato).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
from app.domain.entities.contrato import ArchivoAdjunto, Contrato, TipoArchivo
from app.domain.entities.otrosi import Otrosi
from app.domain.entities.user import User
from app.domain.exceptions import (
    ContratoNotFoundError,
    InvalidContratoStateError,
    UnauthorizedError,
)
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.tipo_otrosi import TipoOtrosi
from app.domain.value_objects.unidad_plazo import UnidadPlazo


@dataclass
class ArchivoOtrosi:
    nombre_original: str
    mime_type: str
    contenido: bytes


@dataclass
class AplicarOtrosiResultado:
    contrato: Contrato
    otrosi: Otrosi


class AplicarOtrosi:
    def __init__(self, contratos: ContratoRepository, storage: FileStorage) -> None:
        self._contratos = contratos
        self._storage = storage

    def execute(
        self,
        actor: User,
        contrato_id: int,
        tipo: TipoOtrosi,
        descripcion: str,
        plazo_adicional_cantidad: Optional[int] = None,
        valor_adicional: Optional[Decimal] = None,
        nueva_descripcion_servicio: Optional[str] = None,
        archivo: Optional[ArchivoOtrosi] = None,
    ) -> AplicarOtrosiResultado:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")

        puede_aplicar = actor.is_admin() or actor.is_juridica() or (
            actor.is_compras() and contrato.creado_por_id == actor.id
        )
        if not puede_aplicar:
            raise UnauthorizedError(
                "Sólo Jurídica/Admin o el comprador que creó el contrato pueden aplicar otrosíes."
            )
        if actor.is_compras() and archivo is not None:
            raise UnauthorizedError(
                "Compras no puede adjuntar el otrosí firmado. "
                "Ese PDF sólo lo carga Jurídica después de aprobación de Líder y Gerencia."
            )
        if actor.is_compras() and plazo_adicional_cantidad is not None:
            raise UnauthorizedError(
                "Compras no puede fijar los tiempos del contrato. "
                "Solicita la prórroga y Jurídica definirá el plazo al finalizar."
            )
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )

        if contrato.estado != EstadoContrato.ACTIVO:
            raise InvalidContratoStateError(
                "Sólo se pueden aplicar otrosíes a contratos en estado ACTIVO. "
                f"Estado actual: {contrato.estado.value}."
            )

        descripcion = (descripcion or "").strip()
        if not descripcion:
            raise ValueError("La descripción / motivo del otrosí es obligatoria.")

        # Validaciones según el tipo
        plazo_aplicar: Optional[int] = None
        valor_aplicar: Optional[Decimal] = None
        nueva_desc_aplicar: Optional[str] = None

        if tipo == TipoOtrosi.PRORROGA:
            # Compras sólo solicita la prórroga; Jurídica define el plazo al finalizar.
            if not actor.is_compras():
                if not plazo_adicional_cantidad or plazo_adicional_cantidad <= 0:
                    raise ValueError(
                        "Para una prórroga debes indicar una cantidad de plazo "
                        "adicional mayor a 0."
                    )
                plazo_aplicar = plazo_adicional_cantidad

        elif tipo == TipoOtrosi.ADICION:
            if valor_adicional is None or Decimal(valor_adicional) <= 0:
                raise ValueError(
                    "Para una adición debes indicar un valor adicional mayor a 0."
                )
            valor_aplicar = Decimal(valor_adicional)

        elif tipo == TipoOtrosi.MODIFICACION:
            if not nueva_descripcion_servicio or not nueva_descripcion_servicio.strip():
                raise ValueError(
                    "Para una modificación debes indicar la nueva descripción "
                    "del servicio."
                )
            nueva_desc_aplicar = nueva_descripcion_servicio.strip()

        # 1) Si hay PDF, lo guardamos primero y obtenemos su id
        archivo_id: Optional[int] = None
        if archivo is not None:
            stored = self._storage.save(
                contenido=archivo.contenido,
                nombre_original=archivo.nombre_original,
                mime_type=archivo.mime_type,
                subcarpeta="contratos",
            )
            archivo_creado = self._contratos.add_archivo(
                ArchivoAdjunto(
                    tipo=TipoArchivo.OTROSI,
                    nombre_original=stored.nombre_original,
                    ruta_almacenamiento=stored.ruta,
                    mime_type=stored.mime_type,
                    tamano_bytes=stored.tamano_bytes,
                    contrato_id=contrato_id,
                    subido_por_id=actor.id,
                )
            )
            archivo_id = archivo_creado.id

        if actor.is_compras():
            otrosi = Otrosi(
                contrato_id=contrato_id,
                numero=contrato.proximo_numero_otrosi(),
                tipo=tipo,
                descripcion=descripcion,
                plazo_adicional_cantidad=plazo_aplicar,
                plazo_adicional_unidad=(
                    contrato.plazo_unidad if plazo_aplicar is not None else None
                ),
                valor_adicional=valor_aplicar,
                nueva_descripcion_servicio=nueva_desc_aplicar,
                archivo_id=None,
                estado_aprobacion=EstadoAprobacion.PENDIENTE_LIDER,
                creado_por_id=actor.id,
            )
            otrosi_creado = self._contratos.add_otrosi(otrosi)
            final = self._contratos.get_by_id(contrato_id)
            return AplicarOtrosiResultado(contrato=final, otrosi=otrosi_creado)

        # 2) Jurídica/Admin aplican los cambios al contrato y finalizan el otrosí
        plazo_unidad_efectiva = contrato.plazo_unidad
        if plazo_aplicar is not None:
            contrato.plazo_cantidad = contrato.plazo_cantidad + plazo_aplicar
        if valor_aplicar is not None:
            contrato.valor = (contrato.valor or Decimal("0")) + valor_aplicar
        if nueva_desc_aplicar is not None:
            contrato.descripcion_servicio = nueva_desc_aplicar

        contrato_actualizado = self._contratos.update(contrato)

        # 3) Registramos el otrosí
        otrosi = Otrosi(
            contrato_id=contrato_id,
            numero=contrato.proximo_numero_otrosi(),
            tipo=tipo,
            descripcion=descripcion,
            plazo_adicional_cantidad=plazo_aplicar,
            plazo_adicional_unidad=(
                plazo_unidad_efectiva if plazo_aplicar is not None else None
            ),
            valor_adicional=valor_aplicar,
            nueva_descripcion_servicio=nueva_desc_aplicar,
            archivo_id=archivo_id,
            estado_aprobacion=EstadoAprobacion.APROBADO,
            aprobado_lider_at=datetime.now(),
            aprobado_gerencia_at=datetime.now(),
            creado_por_id=actor.id,
        )
        otrosi_creado = self._contratos.add_otrosi(otrosi)

        # Refrescamos el contrato para que incluya el otrosí recién creado.
        final = self._contratos.get_by_id(contrato_id)
        return AplicarOtrosiResultado(contrato=final, otrosi=otrosi_creado)
