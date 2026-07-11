"""Estados del flujo de trabajo — Gestión de Solicitudes a Compras."""

from enum import Enum


class EstadoSolicitudGestion(str, Enum):
    SOLICITUD = "solicitud"
    PRIMERA_APROBACION = "primera_aprobacion"
    COTIZACION = "cotizacion"
    EN_APROBACION = "en_aprobacion"
    GESTIONANDO_SERVICIO = "gestionando_servicio"
    PENDIENTE_EVIDENCIA_CIERRE = "pendiente_evidencia_cierre"
    TRAMITANDO_OC = "tramitando_oc"
    TRAMITADA_OC = "tramitada_oc"
    ITEMS_EN_CAMINO = "items_en_camino"
    RECEPCION_INSUMOS = "recepcion_insumos"
    APROBACION_ANTICIPO = "aprobacion_anticipo"
    GESTION_ANTICIPO = "gestion_anticipo"
    CANCELADO = "cancelado"
    ENTREGADO = "entregado"
    ENTREGADO_PARCIAL = "entregado_parcial"
    FACTURADA = "facturada"

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
    EstadoSolicitudGestion.GESTIONANDO_SERVICIO: "Gestionando servicio",
    EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE: "Pendiente evidencia cierre",
    EstadoSolicitudGestion.TRAMITANDO_OC: "Tramitando OC",
    EstadoSolicitudGestion.TRAMITADA_OC: "Tramitada OC",
    EstadoSolicitudGestion.ITEMS_EN_CAMINO: "Ítems en camino",
    EstadoSolicitudGestion.RECEPCION_INSUMOS: "Recepción de Insumos",
    EstadoSolicitudGestion.APROBACION_ANTICIPO: "Aprobación anticipo",
    EstadoSolicitudGestion.GESTION_ANTICIPO: "Gestión anticipo",
    EstadoSolicitudGestion.CANCELADO: "Cancelado",
    EstadoSolicitudGestion.ENTREGADO: "Entregado",
    EstadoSolicitudGestion.ENTREGADO_PARCIAL: "Entrega parcial realizada",
    EstadoSolicitudGestion.FACTURADA: "Facturada",
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
    EstadoSolicitudGestion.GESTIONANDO_SERVICIO,
    EstadoSolicitudGestion.TRAMITANDO_OC,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.ENTREGADO,
]

# Orden visual completo en el historial (incluye ramas finales)
FLUJO_HISTORIAL: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.GESTIONANDO_SERVICIO,
    EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE,
    EstadoSolicitudGestion.TRAMITANDO_OC,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.ITEMS_EN_CAMINO,
    EstadoSolicitudGestion.RECEPCION_INSUMOS,
    EstadoSolicitudGestion.APROBACION_ANTICIPO,
    EstadoSolicitudGestion.GESTION_ANTICIPO,
    EstadoSolicitudGestion.CANCELADO,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
    EstadoSolicitudGestion.FACTURADA,
]

ESTADOS_TERMINALES: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.CANCELADO,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.FACTURADA,
]

ESTADOS_ENTREGA_ABIERTA: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.RECEPCION_INSUMOS,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
]

ESTADOS_RECEPCION_ABIERTA: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.ITEMS_EN_CAMINO,
    EstadoSolicitudGestion.RECEPCION_INSUMOS,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
]

ETAPAS_PENDIENTES_APROBACION: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.REGISTRADA,
    EstadoSolicitudGestion.APROBACION_LIDER_AREA,
]

ETAPAS_PENDIENTES_APROBACION_ANTICIPO: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.APROBACION_ANTICIPO,
]

ETAPAS_GESTION_ANTICIPO: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.GESTION_ANTICIPO,
]

# Solicitudes visibles en el panel de gestión (ya aprobadas al menos una vez).
ETAPAS_PANEL_GESTION: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.GESTIONANDO_SERVICIO,
    EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE,
    EstadoSolicitudGestion.TRAMITANDO_OC,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.ITEMS_EN_CAMINO,
    EstadoSolicitudGestion.RECEPCION_INSUMOS,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
    EstadoSolicitudGestion.FACTURADA,
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
        raw = (str(valor or "")).strip().lower()
        if not raw:
            return EstadoSolicitudGestion.SOLICITUD
        try:
            estado = EstadoSolicitudGestion(raw)
        except ValueError:
            # Valores válidos en BD que aún no estén en el enum cargado en memoria.
            if raw == "gestionando_servicio":
                return EstadoSolicitudGestion.GESTIONANDO_SERVICIO
            if raw == "pendiente_evidencia_cierre":
                return EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE
            if raw == "tramitando_oc":
                return EstadoSolicitudGestion.TRAMITANDO_OC
            if raw == "aprobacion_anticipo":
                return EstadoSolicitudGestion.APROBACION_ANTICIPO
            if raw == "gestion_anticipo":
                return EstadoSolicitudGestion.GESTION_ANTICIPO
            if raw == "items_en_camino":
                return EstadoSolicitudGestion.ITEMS_EN_CAMINO
            if raw == "recepcion_insumos":
                return EstadoSolicitudGestion.RECEPCION_INSUMOS
            if raw == "facturada":
                return EstadoSolicitudGestion.FACTURADA
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


def es_estado_entrega_abierta(estado: EstadoSolicitudGestion | str) -> bool:
    return normalizar_estado(estado) in ESTADOS_ENTREGA_ABIERTA


def es_estado_recepcion_abierta(estado: EstadoSolicitudGestion | str) -> bool:
    return normalizar_estado(estado) in ESTADOS_RECEPCION_ABIERTA


def es_visible_en_panel(estado: EstadoSolicitudGestion | str) -> bool:
    """True si la solicitud ya fue aprobada y debe gestionarse en el panel."""
    normalizado = normalizar_estado(estado)
    if normalizado == EstadoSolicitudGestion.CANCELADO:
        return False
    return normalizado in ETAPAS_PANEL_GESTION


def estado_publico(estado: EstadoSolicitudGestion | str) -> EstadoSolicitudGestion:
    """Estado visible para solicitantes y aprobadores (oculta cierre interno)."""
    normalizado = normalizar_estado(estado)
    if normalizado == EstadoSolicitudGestion.FACTURADA:
        return EstadoSolicitudGestion.ENTREGADO
    return normalizado
