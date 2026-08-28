"""Estados del flujo de trabajo — Gestión de Solicitudes a Compras."""

from enum import Enum


class EstadoSolicitudGestion(str, Enum):
    SOLICITUD = "solicitud"
    REVISION = "revision"
    PRIMERA_APROBACION = "primera_aprobacion"
    # Comité técnico: tras la 1.ª aprobación, Proyectos revisa y puede reescribir
    # la solicitud antes de cotizar.
    REVISION_PROYECTOS = "revision_proyectos"
    # Visita previa a cotizar: si el solicitante marcó "requiere visita", Compras
    # (flujo normal) o Proyectos (comité) agenda proveedor + fecha + hora antes de cotizar.
    PROGRAMACION_VISITA = "programacion_visita"
    # Comité técnico: el rol Proyectos cotiza antes de que Compras complete.
    COTIZACION_PROYECTOS = "cotizacion_proyectos"
    COTIZACION = "cotizacion"
    EN_APROBACION = "en_aprobacion"
    # Comité técnico: reunión posterior a la aprobación de gerencia; supervisor
    # y proyectos deben estar de acuerdo antes de radicar el servicio.
    COMITE = "comite"
    GESTIONANDO_SERVICIO = "gestionando_servicio"
    # Sólo historial (el estado de la SRV no cambia): trazabilidad con Jurídica.
    EN_JURIDICA = "en_juridica"
    SOLICITANDO_INFO = "solicitando_info"
    INFO_RECIBIDA = "info_recibida"
    ELABORANDO_CONTRATO = "elaborando_contrato"
    REVISION_POLIZAS = "revision_polizas"
    SOLICITUD_FIRMAS = "solicitud_firmas"
    ANTICIPO_CONTABILIDAD = "anticipo_contabilidad"
    ANTICIPO_TESORERIA = "anticipo_tesoreria"
    ANTICIPO_PAGADO = "anticipo_pagado"
    CONTRATO_ACTIVO = "contrato_activo"
    CONTRATO_FINALIZADO = "contrato_finalizado"
    # Cierre del contrato: pago final Contabilidad → Tesorería → Completado.
    CIERRE_CONTABILIDAD = "cierre_contabilidad"
    CIERRE_TESORERIA = "cierre_tesoreria"
    CONTRATO_COMPLETADO = "contrato_completado"
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
    EstadoSolicitudGestion.REVISION: "En revisión (ajustes al solicitante)",
    EstadoSolicitudGestion.PRIMERA_APROBACION: "Primera Aprobación",
    EstadoSolicitudGestion.REVISION_PROYECTOS: "Revisión de solicitud (Proyectos)",
    EstadoSolicitudGestion.PROGRAMACION_VISITA: "Programar visita",
    EstadoSolicitudGestion.COTIZACION_PROYECTOS: "Cotización (Proyectos)",
    EstadoSolicitudGestion.COTIZACION: "Cotización",
    EstadoSolicitudGestion.EN_APROBACION: "En Aprobación",
    EstadoSolicitudGestion.COMITE: "Comité técnico",
    EstadoSolicitudGestion.GESTIONANDO_SERVICIO: "Gestionando servicio",
    EstadoSolicitudGestion.EN_JURIDICA: "En Jurídica",
    EstadoSolicitudGestion.SOLICITANDO_INFO: "Solicitando información",
    EstadoSolicitudGestion.INFO_RECIBIDA: "Información recibida",
    EstadoSolicitudGestion.ELABORANDO_CONTRATO: "Elaborando contrato",
    EstadoSolicitudGestion.REVISION_POLIZAS: "Revisión de pólizas",
    EstadoSolicitudGestion.SOLICITUD_FIRMAS: "Solicitud de firmas",
    EstadoSolicitudGestion.ANTICIPO_CONTABILIDAD: "Anticipo en contabilidad",
    EstadoSolicitudGestion.ANTICIPO_TESORERIA: "Anticipo en tesorería",
    EstadoSolicitudGestion.ANTICIPO_PAGADO: "Anticipo pagado",
    EstadoSolicitudGestion.CONTRATO_ACTIVO: "Contrato activo",
    EstadoSolicitudGestion.CONTRATO_FINALIZADO: "Contrato finalizado",
    EstadoSolicitudGestion.CIERRE_CONTABILIDAD: "Cierre en contabilidad",
    EstadoSolicitudGestion.CIERRE_TESORERIA: "Cierre en tesorería",
    EstadoSolicitudGestion.CONTRATO_COMPLETADO: "Contrato completado",
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
    EstadoSolicitudGestion.REVISION_PROYECTOS,
    EstadoSolicitudGestion.PROGRAMACION_VISITA,
    EstadoSolicitudGestion.COTIZACION_PROYECTOS,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.COMITE,
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
    EstadoSolicitudGestion.CONTRATO_FINALIZADO,
    EstadoSolicitudGestion.CONTRATO_COMPLETADO,
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

# Solicitudes en gestión activa (ya aprobadas, aún no completadas).
# Las completadas (entregado/facturada/contrato finalizado) van a ETAPAS_PANEL_REALIZADAS.
ETAPAS_PANEL_GESTION: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.PROGRAMACION_VISITA,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.GESTIONANDO_SERVICIO,
    EstadoSolicitudGestion.PENDIENTE_EVIDENCIA_CIERRE,
    EstadoSolicitudGestion.TRAMITANDO_OC,
    EstadoSolicitudGestion.TRAMITADA_OC,
    EstadoSolicitudGestion.ITEMS_EN_CAMINO,
    EstadoSolicitudGestion.RECEPCION_INSUMOS,
    EstadoSolicitudGestion.ENTREGADO_PARCIAL,
    # Valores legacy ya normalizados en consultas
    EstadoSolicitudGestion.APROBADA,
    EstadoSolicitudGestion.APROBACION_GERENCIA,
    EstadoSolicitudGestion.PROCESO_COTIZACION,
    EstadoSolicitudGestion.EN_PROCESO,
    EstadoSolicitudGestion.PENDIENTE,
]

# Comité técnico: etapas donde actúan Proyectos y el comité (fuera del panel de Compras).
ETAPAS_COMITE_TECNICO: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.REVISION_PROYECTOS,
    EstadoSolicitudGestion.PROGRAMACION_VISITA,
    EstadoSolicitudGestion.COTIZACION_PROYECTOS,
    EstadoSolicitudGestion.COMITE,
]

# Solicitudes ya completadas: pestaña "Realizadas".
ETAPAS_PANEL_REALIZADAS: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.CONTRATO_FINALIZADO,
    EstadoSolicitudGestion.CONTRATO_COMPLETADO,
    EstadoSolicitudGestion.ENTREGADO,
    EstadoSolicitudGestion.FACTURADA,
    EstadoSolicitudGestion.FINALIZADA,  # legacy = entregado
]

# Solicitudes que salen del panel mientras esperan aprobación o anticipo.
ETAPAS_PANEL_EN_PROCESO: list[EstadoSolicitudGestion] = [
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.REVISION,  # devuelta al solicitante para ajustes
    EstadoSolicitudGestion.REVISION_PROYECTOS,  # comité técnico: Proyectos reescribe
    EstadoSolicitudGestion.COTIZACION_PROYECTOS,  # comité técnico: cotiza Proyectos
    EstadoSolicitudGestion.EN_APROBACION,  # 2.ª aprobación (tras mesa técnica)
    EstadoSolicitudGestion.COMITE,  # comité técnico: reunión de aceptación
    EstadoSolicitudGestion.APROBACION_ANTICIPO,
    EstadoSolicitudGestion.GESTION_ANTICIPO,
    # Legacy equivalentes a solicitud pendiente
    EstadoSolicitudGestion.REGISTRADA,
    EstadoSolicitudGestion.APROBACION_LIDER_AREA,
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
            if raw == "revision_proyectos":
                return EstadoSolicitudGestion.REVISION_PROYECTOS
            if raw == "programacion_visita":
                return EstadoSolicitudGestion.PROGRAMACION_VISITA
            if raw == "cotizacion_proyectos":
                return EstadoSolicitudGestion.COTIZACION_PROYECTOS
            if raw == "comite":
                return EstadoSolicitudGestion.COMITE
            if raw == "gestionando_servicio":
                return EstadoSolicitudGestion.GESTIONANDO_SERVICIO
            if raw == "en_juridica":
                return EstadoSolicitudGestion.EN_JURIDICA
            if raw == "solicitando_info":
                return EstadoSolicitudGestion.SOLICITANDO_INFO
            if raw == "info_recibida":
                return EstadoSolicitudGestion.INFO_RECIBIDA
            if raw == "elaborando_contrato":
                return EstadoSolicitudGestion.ELABORANDO_CONTRATO
            if raw == "revision_polizas":
                return EstadoSolicitudGestion.REVISION_POLIZAS
            if raw == "solicitud_firmas":
                return EstadoSolicitudGestion.SOLICITUD_FIRMAS
            if raw == "anticipo_contabilidad":
                return EstadoSolicitudGestion.ANTICIPO_CONTABILIDAD
            if raw == "anticipo_tesoreria":
                return EstadoSolicitudGestion.ANTICIPO_TESORERIA
            if raw == "anticipo_pagado":
                return EstadoSolicitudGestion.ANTICIPO_PAGADO
            if raw == "contrato_activo":
                return EstadoSolicitudGestion.CONTRATO_ACTIVO
            if raw == "contrato_finalizado":
                return EstadoSolicitudGestion.CONTRATO_FINALIZADO
            if raw == "cierre_contabilidad":
                return EstadoSolicitudGestion.CIERRE_CONTABILIDAD
            if raw == "cierre_tesoreria":
                return EstadoSolicitudGestion.CIERRE_TESORERIA
            if raw == "contrato_completado":
                return EstadoSolicitudGestion.CONTRATO_COMPLETADO
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


# Estados anteriores a la aprobación de gerencia financiera (2.ª aprobación),
# más el cancelado. Todo lo demás implica que gerencia ya aprobó.
ETAPAS_PRE_GERENCIA: set[EstadoSolicitudGestion] = {
    EstadoSolicitudGestion.SOLICITUD,
    EstadoSolicitudGestion.REVISION,
    EstadoSolicitudGestion.PRIMERA_APROBACION,
    EstadoSolicitudGestion.PROGRAMACION_VISITA,
    EstadoSolicitudGestion.COTIZACION_PROYECTOS,
    EstadoSolicitudGestion.COTIZACION,
    EstadoSolicitudGestion.EN_APROBACION,
    EstadoSolicitudGestion.CANCELADO,
}


def aprobada_por_gerencia(estado: EstadoSolicitudGestion | str) -> bool:
    """True si la solicitud ya pasó la 2.ª aprobación (gerencia financiera)."""
    return normalizar_estado(estado) not in ETAPAS_PRE_GERENCIA


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
    """True si la solicitud ya fue aprobada (gestión activa o ya realizada)."""
    normalizado = normalizar_estado(estado)
    if normalizado == EstadoSolicitudGestion.CANCELADO:
        return False
    return (
        normalizado in ETAPAS_PANEL_GESTION
        or normalizado in ETAPAS_PANEL_REALIZADAS
        or normalizado in ETAPAS_COMITE_TECNICO
    )


def estado_publico(estado: EstadoSolicitudGestion | str) -> EstadoSolicitudGestion:
    """Estado visible para solicitantes y aprobadores (oculta cierre interno)."""
    normalizado = normalizar_estado(estado)
    if normalizado == EstadoSolicitudGestion.FACTURADA:
        return EstadoSolicitudGestion.ENTREGADO
    return normalizado
