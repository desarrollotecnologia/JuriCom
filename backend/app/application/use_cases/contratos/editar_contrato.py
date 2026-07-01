"""Editar datos del contrato desde Jurídica/Admin."""

from datetime import date
from decimal import Decimal
from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.domain.entities.contrato import Contrato
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.unidad_plazo import UnidadPlazo


class EditarContrato:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(
        self,
        actor: User,
        contrato_id: int,
        proveedor_contratista: str,
        nit_proveedor: str,
        descripcion_servicio: str,
        obligaciones_colbeef: str,
        obligaciones_proveedor: str,
        valor: Decimal,
        moneda: Moneda,
        plazo_cantidad: int,
        plazo_unidad: UnidadPlazo,
        renovacion_automatica: bool,
        condiciones_recibido_satisfactorio: str,
        requiere_poliza: bool,
        fecha_inicio: Optional[date],
        fecha_fin: Optional[date],
        fecha_proxima_notificacion: Optional[date],
    ) -> Contrato:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError("Sólo Jurídica o Admin pueden editar contratos.")

        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )

        self._validar_textos(
            proveedor_contratista,
            nit_proveedor,
            descripcion_servicio,
            obligaciones_colbeef,
            obligaciones_proveedor,
            condiciones_recibido_satisfactorio,
        )
        if valor is None or Decimal(valor) <= 0:
            raise ValueError("El valor del contrato debe ser mayor a 0.")
        if plazo_cantidad <= 0:
            raise ValueError("El plazo debe ser mayor a 0.")
        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio:
            raise ValueError("La fecha fin no puede ser anterior a la fecha inicio.")

        contrato.proveedor_contratista = proveedor_contratista.strip()
        contrato.nit_proveedor = nit_proveedor.strip()
        contrato.descripcion_servicio = descripcion_servicio.strip()
        contrato.obligaciones_colbeef = obligaciones_colbeef.strip()
        contrato.obligaciones_proveedor = obligaciones_proveedor.strip()
        contrato.valor = Decimal(valor)
        contrato.moneda = moneda
        contrato.plazo_cantidad = plazo_cantidad
        contrato.plazo_unidad = plazo_unidad
        contrato.renovacion_automatica = renovacion_automatica
        contrato.condiciones_recibido_satisfactorio = (
            condiciones_recibido_satisfactorio.strip()
        )
        contrato.requiere_poliza = requiere_poliza
        contrato.fecha_inicio = fecha_inicio
        contrato.fecha_fin = fecha_fin
        contrato.fecha_proxima_notificacion = fecha_proxima_notificacion

        return self._contratos.update(contrato)

    @staticmethod
    def _validar_textos(*valores: str) -> None:
        if any(not v or not str(v).strip() for v in valores):
            raise ValueError("Todos los campos de texto obligatorios deben estar llenos.")
