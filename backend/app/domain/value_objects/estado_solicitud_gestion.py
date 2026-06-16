"""Estados del flujo de trabajo — Gestión de Solicitudes a Compras."""

from enum import Enum


class EstadoSolicitudGestion(str, Enum):
    SOLICITUD = "solicitud"
    PRIMERA_APROBACION = "primera_aprobacion"
    COTIZACION = "cotizacion"
    EN_APROBACION = "en_aprobacion"
    TRAMITADA_OC = "tramitada_oc"
    CANCELADO = "cancelado"
    ENTREGADO = "entregado"
    ENTREGADO_PARCIAL = "entregado_parcial"

    # Valores legacy
    REGISTRADA = "registrada"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    APROBACION_LIDER_AREA = "aprobacion_lider_area"
    APROBACION_GERENCIA = "aprobacion_gerencia"
    PROCESO_COTIZACION = "proceso_cotizacion"
    EN_PROCESO = "en_proceso"
    PENDIENTE = "pendiente"
    FINALIZADA = "finalizada"

    @property
    def label(self) -> str:
        return LABELS.get(self, self.value)

    @property
    def es_flujo(self) -> bool:
        return self in FLUJO_ORDEN or self in ESTADOS_TERMINALES


LABELS: dict[EstadoSolicitudGestion, str] = {
    EstadoSolicitudGestion.SOLICITUD: "Solicitud",
    EstadoSolicitudGestion.PRIMERA_APROBACION: "Primera Aprobación",
    EstadoSolicitudGestion.COTIZACION: "Cotización",
    EstadoSolicitudGestion.EN_APROBACION: "En Aprobación",
    EstadoSolicitudGestion.TRAMITADA_OC: "Tramitada OC",
    EstadoSolicitudGestion.CANCELADO: "Cancelado",
    EstadoSolicitudGestion.ENTREGADO: "Entregado",
    EstadoSolicitudGestion.ENTREGADO_PARCIAL: "Entregado Parcial",
    EstadoSolicitudGestion.REGISTRADA: "Solicitud",
    EstadoSolicitudGestion.APROBADA: "Primera Aprobación",
    EstadoSolicitudGestion.RECHAZADA: "Cancelado",
}

# Progresión principal (sin ramas terminales alternativas)
FLUJO_ORDEN: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.ENTREGADO,
]

# Orden visual completo en el historial (incluye ramas finales)
FLUJO_HISTORIAL: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.CANCELADO,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
]

ESTADOS_TERMINALES: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.CANCELADO,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
]

ETAPAS_PENDIENTES_APROBACION: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.REGISTRADA,
    EstadoSolicitudGestion.APROBACION_LIDER_AREA,
]

# Solicitudes visibles en el panel de gestión (ya aprobadas al menos una vez).
ETAPAS_PANEL_GESTION: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
    # Valores legacy ya normalizados en consultas
    EstadoSolicitudGestion.APROBADA,
    EstadoSolicitudGestion.APROBACION_GERENCIA,
    EstadoSolicitudGestion.PROCESO_COTIZACION,
    EstadoSolicitudGestion.EN_PROCESO,
    EstadoSolicitudGestion.PENDIENTE,
    EstadoSolicitudGestion.FINALIZADA,
]

_LEGACY_MAP: dict[str, EstadoSolicitudGestion] = {
    EstadoSolicitudGestion.REGISTRADA.value: EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.APROBADA.value: EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.RECHAZADA.value: EstadoSolicitudGestion.CANCELADO,
    EstadoSolicitudGestion.APROBACION_LIDER_AREA.value: EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.APROBACION_GERENCIA.value: EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.PROCESO_COTIZACION.value: EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_PROCESO.value: EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.PENDIENTE.value: EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.FINALIZADA.value: EstadoSolicitudGestion.ENTREGADO,
}


def normalizar_estado(valor: str | EstadoSolicitudGestion) -> EstadoSolicitudGestion:
    if isinstance(valor, EstadoSolicitudGestion):
        estado = valor
    else:
        try:
            estado = EstadoSolicitudGestion(valor)
        except ValueError:
            return EstadoSolicitudGestion.SOLICITUD
    return _LEGACY_MAP.get(estado.value, estado)


def indice_etapa(estado: EstadoSolicitudGestion) -> int:
    normalizado = normalizar_estado(estado)
    try:
        return FLUJO_HISTORIAL.index(normalizado)
    except ValueError:
        return 0


def indice_flujo(estado: EstadoSolicitudGestion) -> int:
    normalizado = normalizar_estado(estado)
    if normalizado in ESTADOS_TERMINALES:
        return -1
    try:
        return FLUJO_ORDEN.index(normalizado)
    except ValueError:
        return 0


def siguiente_etapa(estado: EstadoSolicitudGestion) -> EstadoSolicitudGestion | None:
    actual = normalizar_estado(estado)
    if actual in ESTADOS_TERMINALES:
        return None
    idx = indice_flujo(actual)
    if idx < 0 or idx >= len(FLUJO_ORDEN) - 1:
        return None
    return FLUJO_ORDEN[idx + 1]


def es_pendiente_aprobacion(estado: EstadoSolicitudGestion) -> bool:
    normalizado = normalizar_estado(estado)
    return normalizado in (
        EstadoSolicitudGestion.SOLICITUD,
        EstadoSolicitudGestion.EN_APROBACION,
    )


def es_estado_terminal(estado: EstadoSolicitudGestion) -> bool:
    return normalizar_estado(estado) in ESTADOS_TERMINALES


def es_visible_en_panel(estado: EstadoSolicitudGestion | str) -> bool:
    """True si la solicitud ya fue aprobada y debe gestionarse en el panel."""
    normalizado = normalizar_estado(estado)
    if normalizado == EstadoSolicitudGestion.CANCELADO:
        return False
    return normalizado in ETAPAS_PANEL_GESTION
