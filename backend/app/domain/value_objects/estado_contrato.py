"""Estados de un contrato.

Flujo típico:
    EN_PROCESO  → ACTIVO       (cuando ya se firmó / quedó completo)
    ACTIVO      → FINALIZADO   (cuando se vence o no se renueva)

El estado inicial al radicar es EN_PROCESO (porque le faltan documentos
de jurídica: póliza si aplica, contrato firmado, etc.).

Sólo Jurídica y Admin pueden cambiar el estado.
"""

from enum import Enum


class EstadoContrato(str, Enum):
    EN_PROCESO = "en_proceso"
    ELABORANDO = "elaborando"
    REVISION_POLIZAS = "revision_polizas"
    SOLICITUD_FIRMAS = "solicitud_firmas"
    ANTICIPO_CONTABILIDAD = "anticipo_contabilidad"
    ANTICIPO_TESORERIA = "anticipo_tesoreria"
    ANTICIPO_PAGADO = "anticipo_pagado"
    ACTIVO = "activo"
    FINALIZADO = "finalizado"
    # Cierre del contrato (tras informe/acta): pago final gestionado por
    # Contabilidad → Tesorería. Al confirmar Tesorería queda COMPLETADO (terminal).
    CIERRE_CONTABILIDAD = "cierre_contabilidad"
    CIERRE_TESORERIA = "cierre_tesoreria"
    COMPLETADO = "completado"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]

    @property
    def label(self) -> str:
        return {
            EstadoContrato.EN_PROCESO: "En proceso",
            EstadoContrato.ELABORANDO: "Elaborando contrato",
            EstadoContrato.REVISION_POLIZAS: "Revisión de pólizas",
            EstadoContrato.SOLICITUD_FIRMAS: "Solicitud de firmas",
            EstadoContrato.ANTICIPO_CONTABILIDAD: "Anticipo en contabilidad",
            EstadoContrato.ANTICIPO_TESORERIA: "Anticipo en tesorería",
            EstadoContrato.ANTICIPO_PAGADO: "Anticipo pagado",
            EstadoContrato.ACTIVO: "Activo",
            EstadoContrato.FINALIZADO: "Finalizado",
            EstadoContrato.CIERRE_CONTABILIDAD: "Cierre en contabilidad",
            EstadoContrato.CIERRE_TESORERIA: "Cierre en tesorería",
            EstadoContrato.COMPLETADO: "Completado",
        }[self]
