"""Caso de uso: cambiar el estado de un contrato.

Sólo Jurídica y Admin pueden hacerlo.
Reglas de negocio:
- Para pasar a ACTIVO primero debe adjuntarse el contrato firmado.
- La póliza NO se exige para activar: la sube Jurídica/Gerencia durante la elaboración.
- FINALIZADO es estado terminal (se puede volver a abrir si fuese necesario,
  pero la operación normal es de un solo paso).
"""

from datetime import date, datetime, time, timedelta

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.use_cases.contratos.radicar_solicitud import calcular_fecha_fin
from app.domain.entities.contrato import Contrato, HORA_NOTIFICACION_DEFAULT
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato


class CambiarEstadoContrato:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(
        self, actor: User, contrato_id: int, nuevo_estado: EstadoContrato
    ) -> Contrato:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica o el Administrador pueden cambiar el estado."
            )

        if nuevo_estado in (EstadoContrato.FINALIZADO, EstadoContrato.COMPLETADO):
            raise ValueError(
                "La finalización del contrato la realiza Compras adjuntando el "
                "informe final (y el acta de liquidación cuando aplique); el pago "
                "final lo confirman Contabilidad y Tesorería."
            )

        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )

        # Mientras el anticipo lo gestionan Contabilidad/Tesorería, Jurídica no puede
        # cambiar el estado manualmente (evita sacar el contrato del sub-flujo y que
        # nunca llegue a Tesorería). Sale del flujo sólo al confirmar el pago.
        if (
            contrato.estado
            in (
                EstadoContrato.ANTICIPO_CONTABILIDAD,
                EstadoContrato.ANTICIPO_TESORERIA,
            )
            and nuevo_estado != contrato.estado
        ):
            raise ValueError(
                "El anticipo está en gestión de Contabilidad/Tesorería. No se puede "
                "cambiar el estado manualmente hasta que Tesorería confirme el pago."
            )

        # Igual para el cierre final: mientras Contabilidad/Tesorería gestionan el pago
        # final, Jurídica no puede sacar el contrato del sub-flujo.
        if (
            contrato.estado
            in (
                EstadoContrato.CIERRE_CONTABILIDAD,
                EstadoContrato.CIERRE_TESORERIA,
            )
            and nuevo_estado != contrato.estado
        ):
            raise ValueError(
                "El cierre está en gestión de Contabilidad/Tesorería. No se puede "
                "cambiar el estado manualmente hasta que Tesorería confirme el pago final."
            )

        if nuevo_estado == EstadoContrato.ACTIVO and not contrato.tiene_borrador():
            raise ValueError(
                "No se puede marcar como ACTIVO: primero adjunta el contrato "
                "firmado. La póliza la sube Jurídica o Gerencia durante la elaboración."
            )

        # Gating del anticipo: si el contrato tiene anticipo, Contabilidad debe
        # gestionarlo y Tesorería confirmar el pago antes de poder activarlo.
        if (
            nuevo_estado == EstadoContrato.ACTIVO
            and getattr(contrato, "requiere_anticipo", False)
            and not getattr(contrato, "anticipo_pagado", False)
        ):
            raise ValueError(
                "No se puede activar: el anticipo debe ser gestionado por "
                "Contabilidad y el pago confirmado por Tesorería."
            )

        contrato.estado = nuevo_estado
        # Al entrar en elaboración arranca el plazo de 2 días hábiles.
        # (Antes se fijaba al aprobar gerencia; ahora la aprobación viene de la SRV.)
        if (
            nuevo_estado == EstadoContrato.ELABORANDO
            and contrato.aprobado_gerencia_at is None
        ):
            contrato.aprobado_gerencia_at = datetime.now()
        if nuevo_estado == EstadoContrato.ACTIVO:
            self._asegurar_fechas_vigencia(contrato)
            if contrato.fecha_inicio and contrato.fecha_inicio_original is None:
                contrato.fecha_inicio_original = contrato.fecha_inicio
        return self._contratos.update(contrato)

    @staticmethod
    def _asegurar_fechas_vigencia(contrato: Contrato) -> None:
        if contrato.fecha_inicio is None:
            contrato.fecha_inicio = date.today()
        if contrato.fecha_fin is None:
            contrato.fecha_fin = calcular_fecha_fin(
                contrato.fecha_inicio,
                contrato.plazo_cantidad,
                contrato.plazo_unidad,
            )
        if contrato.fecha_proxima_notificacion is None:
            contrato.fecha_proxima_notificacion = max(
                contrato.fecha_inicio,
                contrato.fecha_fin - timedelta(days=30),
            )
        if contrato.hora_proxima_notificacion is None:
            contrato.hora_proxima_notificacion = HORA_NOTIFICACION_DEFAULT
