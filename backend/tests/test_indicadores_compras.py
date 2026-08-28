from datetime import datetime
from decimal import Decimal

from app.application.services.indicadores_compras import calcular_indicadores_compras
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


def _srv(**kwargs) -> SolicitudGestion:
    base = dict(tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS, titulo="x", creado_por_id=1)
    base.update(kwargs)
    return SolicitudGestion(**base)


def test_rankings_area_y_proveedor():
    solicitudes = [
        _srv(
            codigo="SRV-0001",
            created_at=datetime(2026, 8, 1),
            estado=EstadoSolicitudGestion.GESTIONANDO_SERVICIO,
            centro_costo_area="Producción",
            proveedor_sugerido="DISAN — 3001234567 — ventas@disan.com",
            valor_tramite_oc=Decimal("1000"),
        ),
        _srv(
            codigo="SRV-0002",
            created_at=datetime(2026, 8, 2),
            estado=EstadoSolicitudGestion.CONTRATO_FINALIZADO,
            centro_costo_area="Producción",
            # misma empresa en minúscula + otra línea: debe agrupar DISAN y contar OTRO una vez
            proveedor_sugerido="disan — 3009999999\nOTRO SAS — comercio",
            valor_tramite_oc=Decimal("3000"),
        ),
        _srv(
            created_at=datetime(2026, 8, 3),
            estado=EstadoSolicitudGestion.TRAMITADA_OC,
            centro_costo_area="Mantenimiento",
            proveedor_sugerido="OTRO SAS — comercio",
            valor_tramite_oc=Decimal("2000"),
        ),
        # Servicio del mes AÚN en cotización (no aprobado por gerencia): NO debe contar.
        _srv(
            codigo="SRV-0009",
            created_at=datetime(2026, 8, 4),
            estado=EstadoSolicitudGestion.COTIZACION,
            centro_costo_area="Producción",
            proveedor_sugerido="NO APROBADO SAS — pruebas",
            valor_tramite_oc=Decimal("999999"),
        ),
    ]
    ind = calcular_indicadores_compras(solicitudes, referencia=REF)
    # Producción gasta 4000 > Mantenimiento 2000
    assert ind.areas_gasto[0].etiqueta == "Producción"
    assert ind.areas_gasto[0].valor == 4000.0
    # detalles: códigos de las solicitudes que componen el gasto del área
    assert ind.areas_gasto[0].detalles == ["SRV-0001", "SRV-0002"]
    # DISAN aparece en 2 solicitudes (agrupando mayúsc/minúsc) > OTRO SAS en 2 también.
    # DISAN debe salir con nombre display "DISAN".
    proveedores = {p.etiqueta: p.valor for p in ind.proveedores_frecuentes}
    assert proveedores["DISAN"] == 2.0
    assert proveedores["OTRO SAS"] == 2.0
    # El servicio en cotización (no aprobado por gerencia) no aparece.
    assert "NO APROBADO SAS" not in proveedores
    assert all("SRV-0009" not in it.detalles for it in ind.areas_gasto)


REF = datetime(2026, 8, 15, 12, 0, 0)


def test_indicadores_mes_actual():
    solicitudes = [
        # Recibida este mes, aún en gestión.
        _srv(created_at=datetime(2026, 8, 2), estado=EstadoSolicitudGestion.GESTIONANDO_SERVICIO),
        # Recibida el mes pasado, finalizada este mes (gestionada este mes, 5 días de resolución
        # NO aplica porque se creó en julio: cierre - creación).
        _srv(
            created_at=datetime(2026, 8, 1),
            updated_at=datetime(2026, 8, 6),
            estado=EstadoSolicitudGestion.CONTRATO_FINALIZADO,
            valor_tramite_oc=Decimal("1000000"),
        ),
        # Servicio facturado el mes pasado (no cuenta como gestionada del mes actual).
        _srv(
            created_at=datetime(2026, 7, 10),
            updated_at=datetime(2026, 7, 20),
            estado=EstadoSolicitudGestion.FACTURADA,
            valor_tramite_oc=Decimal("500000"),
        ),
        # Compra recibida este mes (no es servicio: no suma a valor_servicios).
        _srv(
            tipo=TipoSolicitudGestion.COMPRA,
            created_at=datetime(2026, 8, 10),
            estado=EstadoSolicitudGestion.TRAMITADA_OC,
            valor_tramite_oc=Decimal("999"),
        ),
    ]

    ind = calcular_indicadores_compras(solicitudes, referencia=REF)

    assert ind.mes == "2026-08"
    # recibidas este mes: la de gestion (ago 2), la finalizada (ago 1), la compra (ago 10) = 3
    assert ind.recibidas_mes == 3
    # gestionadas este mes: solo la finalizada con cierre en agosto = 1
    assert ind.gestionadas_mes == 1
    # resolución: (ago 6 - ago 1) = 5 días
    assert ind.tiempo_resolucion_dias == 5.0
    # valor servicios del mes: solo la de servicios creada en agosto (1.000.000).
    # La facturada se creó en julio, así que ya no suma.
    assert ind.valor_servicios == Decimal("1000000")

    # serie: 6 meses, terminando en el mes de referencia (agosto 2026)
    assert len(ind.serie) == 6
    assert ind.serie[-1].mes == "2026-08"
    assert ind.serie[0].mes == "2026-03"
    agosto = ind.serie[-1]
    julio = ind.serie[-2]
    assert agosto.recibidas == 3
    assert agosto.gestionadas == 1
    assert julio.recibidas == 1  # la facturada se creó en julio
    assert julio.gestionadas == 1  # y se cerró en julio

    # distribución por estado
    assert ind.por_estado["en_gestion"] == 2  # servicio en gestión + compra tramitada
    assert ind.por_estado["realizadas"] == 2  # finalizada + facturada
    assert ind.por_estado["canceladas"] == 0
    # distribución por tipo
    assert ind.por_tipo["servicios"] == 3
    assert ind.por_tipo["compra"] == 1
    assert ind.por_tipo["salidas_almacen"] == 0


def test_sin_datos_del_mes():
    ind = calcular_indicadores_compras([], referencia=REF)
    assert ind.recibidas_mes == 0
    assert ind.gestionadas_mes == 0
    assert ind.tiempo_resolucion_dias is None
    assert ind.valor_servicios == Decimal("0")
