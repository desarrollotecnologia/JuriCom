"""Dashboard de tiempos de atención (solicitudes de Compra y Servicios).

Función pura sobre datos ya cargados para poder testear sin BD:
- Tiempos promedio por etapa (cuellos de botella).
- Requerimientos pendientes (aún sin cerrar) con días detenidos.
- Tiempo total promedio de punta a punta (radica → fin).

Definición de "fin" (según requerimiento del líder financiero):
- Compra: cuando se tramita la OC (TRAMITANDO_OC / TRAMITADA_OC).
- Servicios: cuando se expide el contrato (fecha de creación del contrato).
"""

from datetime import datetime
from typing import Iterable, Optional

from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.value_objects.estado_solicitud_gestion import (
    FLUJO_HISTORIAL,
    EstadoSolicitudGestion,
    normalizar_estado,
)
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios

# Área/rol legible para el tablero (quién atiende cada acción).
_ROL_LABEL = {
    "admin": "Administrador",
    "juridica": "Jurídica",
    "compras": "Compras",
    "solicitante": "Solicitante",
    "anticipos": "Anticipos",
    "lider_aprobador": "Líder aprobador",
    "proyectos": "Proyectos",
    "contabilidad": "Contabilidad",
    "tesoreria": "Tesorería",
}


def _rol_label(rol: str) -> str:
    r = (rol or "").strip()
    return _ROL_LABEL.get(r, r or "—")


# Fin del flujo para una COMPRA: la OC quedó en trámite.
_FIN_ETAPAS_COMPRA = {
    EstadoSolicitudGestion.TRAMITANDO_OC,
    EstadoSolicitudGestion.TRAMITADA_OC,
}


def _dias(desde: datetime, hasta: datetime) -> float:
    return (hasta - desde).total_seconds() / 86400.0


def _norm(etapa: str) -> Optional[EstadoSolicitudGestion]:
    try:
        return normalizar_estado(etapa)
    except Exception:  # etapa legacy/desconocida: la ignoramos
        return None


def _orden_flujo(etapa: EstadoSolicitudGestion) -> int:
    """Posición de la etapa en el flujo inicio→fin (para dibujar el proceso)."""
    try:
        return FLUJO_HISTORIAL.index(etapa)
    except ValueError:
        return len(FLUJO_HISTORIAL)


def _breakdown(
    historial: list[tuple[str, datetime, str, str]], hasta: datetime
) -> list[dict]:
    """Desglose de días que el requerimiento pasó en cada etapa (el 'por qué').

    Cada tramo = tiempo entre dos transiciones; se atribuye a quien ejecutó la
    acción que cerró la etapa (el que finalmente 'contestó').
    """
    tramos: list[dict] = []
    for (etapa_str, t0, _u0, _r0), (_, t1, resp, resprol) in zip(historial, historial[1:]):
        if t1 > hasta:
            break
        etapa = _norm(etapa_str)
        if etapa is None:
            continue
        d = _dias(t0, t1)
        if d < 0:
            continue
        tramos.append(
            {
                "etapa": etapa.value,
                "etapa_label": etapa.label,
                "dias": round(d, 1),
                "responsable": (resp or "").strip(),
                "rol_label": _rol_label(resprol or ""),
            }
        )
    return tramos


def _cuello(tramos: list[dict]) -> dict:
    """Etapa donde más tiempo estuvo (la razón principal de la demora)."""
    if not tramos:
        return {"etapa_label": "", "dias": 0.0, "responsable": "", "rol_label": ""}
    return max(tramos, key=lambda x: x["dias"])


def calcular_dashboard_tiempos(
    solicitudes: Iterable[SolicitudGestion],
    historial_por_sid: dict[int, list[tuple[str, datetime, str]]],
    contrato_fecha_por_sid: dict[int, datetime],
    *,
    ahora: Optional[datetime] = None,
) -> dict:
    ref = ahora or datetime.now()

    # Acumuladores para el promedio por etapa (cuellos de botella).
    etapa_suma: dict[EstadoSolicitudGestion, float] = {}
    etapa_conteo: dict[EstadoSolicitudGestion, int] = {}

    # Tiempo de respuesta por usuario: se atribuye a quien EJECUTÓ la acción
    # el tiempo que el requerimiento estuvo esperando en la etapa anterior.
    usuario_suma: dict[str, float] = {}
    usuario_conteo: dict[str, int] = {}
    usuario_rol: dict[str, str] = {}

    totales_dias: list[float] = []
    pendientes: list[dict] = []
    finalizados: list[dict] = []
    total = 0

    def _tipo_val(x):
        return x.tipo.value if hasattr(x.tipo, "value") else str(x.tipo)

    def _tipo_lbl(x):
        return x.tipo.label if hasattr(x.tipo, "label") else str(x.tipo)

    for s in solicitudes:
        if s.id is None or s.created_at is None:
            continue
        total += 1
        estado = normalizar_estado(s.estado)
        historial = sorted(
            historial_por_sid.get(s.id, []), key=lambda x: x[1]
        )

        # Duración de cada etapa = tiempo entre transiciones consecutivas.
        # La espera en la etapa anterior se atribuye a quien ejecutó la
        # acción siguiente (el que "contestó").
        for (etapa_str, t0, _u0, _r0), (_, t1, resp, resprol) in zip(historial, historial[1:]):
            d = _dias(t0, t1)
            if d < 0:
                continue
            etapa = _norm(etapa_str)
            if etapa is not None:
                etapa_suma[etapa] = etapa_suma.get(etapa, 0.0) + d
                etapa_conteo[etapa] = etapa_conteo.get(etapa, 0) + 1
            nombre = (resp or "").strip()
            if nombre:
                usuario_suma[nombre] = usuario_suma.get(nombre, 0.0) + d
                usuario_conteo[nombre] = usuario_conteo.get(nombre, 0) + 1
                usuario_rol.setdefault(nombre, resprol or "")

        # Fin del flujo (para el tiempo total).
        fin_ts: Optional[datetime] = None
        if es_flujo_servicios(s.tipo):
            fin_ts = contrato_fecha_por_sid.get(s.id)
        else:
            for etapa_str, t, _u, _r in historial:
                if _norm(etapa_str) in _FIN_ETAPAS_COMPRA:
                    fin_ts = t
                    break

        if fin_ts is not None and fin_ts >= s.created_at:
            dt = _dias(s.created_at, fin_ts)
            totales_dias.append(dt)
            tramos = _breakdown(historial, fin_ts)
            cuello = _cuello(tramos)
            finalizados.append(
                {
                    "id": s.id,
                    "codigo": s.codigo or "",
                    "tipo": _tipo_val(s),
                    "tipo_label": _tipo_lbl(s),
                    "titulo": s.titulo or "",
                    "estado": estado.value,
                    "estado_label": estado.label,
                    "solicitante": (s.creado_por_email or "").strip(),
                    "dias_total": round(dt, 1),
                    "etapas": tramos,
                    "cuello_label": cuello["etapa_label"],
                    "cuello_dias": cuello["dias"],
                    "cuello_responsable": cuello["responsable"],
                    "cuello_rol_label": cuello["rol_label"],
                }
            )
            continue

        # Canceladas no cuentan como pendientes ni como finalizadas.
        if estado == EstadoSolicitudGestion.CANCELADO:
            continue

        ultimo_ts = historial[-1][1] if historial else s.created_at
        pendientes.append(
            {
                "id": s.id,
                "codigo": s.codigo or "",
                "tipo": (s.tipo.value if hasattr(s.tipo, "value") else str(s.tipo)),
                "tipo_label": (s.tipo.label if hasattr(s.tipo, "label") else str(s.tipo)),
                "titulo": s.titulo or "",
                "estado": estado.value,
                "estado_label": estado.label,
                "solicitante": (s.creado_por_email or "").strip(),
                "dias_en_etapa": round(_dias(ultimo_ts, ref), 1),
                "dias_total": round(_dias(s.created_at, ref), 1),
            }
        )

    tiempos_por_etapa = [
        {
            "etapa": etapa.value,
            "etapa_label": etapa.label,
            "promedio_dias": round(etapa_suma[etapa] / etapa_conteo[etapa], 1),
            "muestras": etapa_conteo[etapa],
            "orden": _orden_flujo(etapa),
        }
        for etapa in etapa_suma
    ]
    # Cuello de botella primero (mayor promedio).
    tiempos_por_etapa.sort(key=lambda e: e["promedio_dias"], reverse=True)

    tiempos_por_usuario = [
        {
            "usuario": nombre,
            "rol": usuario_rol.get(nombre, ""),
            "rol_label": _rol_label(usuario_rol.get(nombre, "")),
            "promedio_dias": round(usuario_suma[nombre] / usuario_conteo[nombre], 1),
            "respuestas": usuario_conteo[nombre],
        }
        for nombre in usuario_suma
    ]
    # El que más se demora en contestar, primero.
    tiempos_por_usuario.sort(key=lambda u: u["promedio_dias"], reverse=True)

    # Más detenidos primero.
    pendientes.sort(key=lambda p: p["dias_en_etapa"], reverse=True)
    # El que más tardó de inicio a fin, primero.
    finalizados.sort(key=lambda f: f["dias_total"], reverse=True)

    promedio_total = (
        round(sum(totales_dias) / len(totales_dias), 1) if totales_dias else None
    )

    return {
        "total": total,
        "pendientes_count": len(pendientes),
        "finalizadas_count": len(finalizados),
        "tiempo_total_promedio_dias": promedio_total,
        "tiempo_total_muestras": len(totales_dias),
        "tiempos_por_etapa": tiempos_por_etapa,
        "tiempos_por_usuario": tiempos_por_usuario,
        "pendientes": pendientes,
        "finalizados": finalizados,
    }
