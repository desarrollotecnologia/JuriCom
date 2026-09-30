"""Check del servicio de dashboard de tiempos de atención (función pura)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.application.services.dashboard_tiempos_atencion import (
    calcular_dashboard_tiempos,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

AHORA = datetime(2026, 1, 31, 12, 0, 0)


def _sol(sid, tipo, estado, dias_atras, codigo="SG-0001"):
    return SimpleNamespace(
        id=sid,
        codigo=codigo,
        tipo=tipo,
        estado=estado,
        titulo="x",
        creado_por_email="user@colbeef.com",
        created_at=AHORA - timedelta(days=dias_atras),
    )


def test_dashboard_tiempos():
    t = lambda d: AHORA - timedelta(days=d)  # noqa: E731

    solicitudes = [
        _sol(1, TipoSolicitudGestion.COMPRA, "cotizacion", 10, "SG-1"),      # pendiente
        _sol(2, TipoSolicitudGestion.COMPRA, "tramitando_oc", 20, "SG-2"),   # finalizada
        _sol(3, TipoSolicitudGestion.INSUMOS_SERVICIOS, "gestionando_servicio", 30, "SRV-3"),  # fin por contrato
        _sol(4, TipoSolicitudGestion.COMPRA, "cancelado", 5, "SG-4"),        # excluida
    ]
    historial = {
        1: [("solicitud", t(10), "Ana", "solicitante"), ("cotizacion", t(3), "Beto", "compras")],
        2: [("solicitud", t(20), "Ana", "solicitante"), ("cotizacion", t(15), "Beto", "compras"), ("tramitando_oc", t(5), "Ana", "solicitante")],
        3: [("solicitud", t(30), "Ana", "solicitante"), ("cotizacion", t(20), "Carla", "lider_aprobador")],
        4: [("solicitud", t(5), "Ana", "solicitante")],
    }
    contratos = {3: t(2)}  # contrato expedido hace 2 días

    r = calcular_dashboard_tiempos(solicitudes, historial, contratos, ahora=AHORA)

    assert r["total"] == 4
    # Pendiente: solo la #1 (la 4 está cancelada, 2 y 3 finalizaron).
    assert r["pendientes_count"] == 1
    p = r["pendientes"][0]
    assert p["codigo"] == "SG-1"
    assert round(p["dias_en_etapa"]) == 3
    assert round(p["dias_total"]) == 10

    # Finalizadas: compra #2 (15 días) y servicio #3 (28 días).
    assert r["finalizadas_count"] == 2
    assert r["tiempo_total_muestras"] == 2
    assert round(r["tiempo_total_promedio_dias"]) == round((15 + 28) / 2)

    # Lista de finalizados: el que más tardó (servicio #3, 28 días) va primero.
    fin = r["finalizados"]
    assert len(fin) == 2
    assert fin[0]["codigo"] == "SRV-3"
    assert round(fin[0]["dias_total"]) == 28
    assert round(fin[1]["dias_total"]) == 15

    # El "por qué": desglose por etapa y cuello de botella del requerimiento.
    # SG-2 (compra) estuvo 10 días en Cotización (Ana lo movió a trámite OC).
    sg2 = fin[1]
    assert sg2["codigo"] == "SG-2"
    assert round(sg2["cuello_dias"]) == 10
    assert "Cotización" in sg2["cuello_label"]
    assert sg2["cuello_responsable"] == "Ana"
    assert len(sg2["etapas"]) == 2  # solicitud y cotización

    # Cuello de botella: la etapa con mayor promedio va primero.
    etapas = {e["etapa"]: e["promedio_dias"] for e in r["tiempos_por_etapa"]}
    assert "cotizacion" in etapas
    assert r["tiempos_por_etapa"][0]["promedio_dias"] >= r["tiempos_por_etapa"][-1]["promedio_dias"]

    # Tiempo de respuesta por usuario (se atribuye a quien ejecutó la acción).
    usuarios = {u["usuario"]: u for u in r["tiempos_por_usuario"]}
    assert usuarios["Beto"]["respuestas"] == 2
    assert round(usuarios["Beto"]["promedio_dias"]) == 6   # (7 + 5) / 2
    assert round(usuarios["Ana"]["promedio_dias"]) == 10
    assert usuarios["Beto"]["rol_label"] == "Compras"
    assert usuarios["Carla"]["rol_label"] == "Líder aprobador"
    # El más lento va primero.
    assert r["tiempos_por_usuario"][0]["promedio_dias"] >= r["tiempos_por_usuario"][-1]["promedio_dias"]
