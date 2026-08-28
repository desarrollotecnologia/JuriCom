"""Pruebas de humo (smoke) sobre la capa de dominio.

No requieren BD ni FastAPI: validan que las entidades funcionan solas.
Ejecuta con:  python -m pytest backend/tests -q
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.entities.contrato import (
    COMPANIA_DEFAULT,
    Contrato,
    TipoArchivo,
)
from app.domain.entities.user import User
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.roles import Role
from app.domain.value_objects.unidad_plazo import UnidadPlazo


def test_user_permissions():
    admin = User(username="a", password_hash="x", role=Role.ADMIN)
    compras = User(username="b", password_hash="x", role=Role.COMPRAS)
    juridica = User(username="c", password_hash="x", role=Role.JURIDICA)
    solicitante = User(username="d", password_hash="x", role=Role.SOLICITANTE)
    anticipos = User(username="e", password_hash="x", role=Role.ANTICIPOS)
    lider = User(
        username="f",
        password_hash="x",
        role=Role.LIDER_APROBADOR,
        lider_catalog_id="79249780",
    )

    assert admin.can_manage_users() is True
    assert compras.can_manage_users() is False
    assert juridica.can_manage_users() is False
    assert compras.is_compras() and not compras.is_juridica()
    assert compras.puede_aprobar_solicitudes_gestion() is False
    assert compras.puede_aprobar_anticipo_solicitud() is False
    assert compras.puede_operar_anticipos() is False
    assert solicitante.puede_crear_solicitudes_gestion() is True
    assert solicitante.puede_gestionar_panel_compras() is False
    assert solicitante.ve_solo_propias_solicitudes_gestion() is True
    assert anticipos.puede_operar_anticipos() is True
    assert anticipos.puede_crear_solicitudes_gestion() is True
    assert anticipos.ve_solo_propias_solicitudes_gestion() is True
    assert anticipos.puede_aprobar_anticipo_solicitud() is False
    assert lider.puede_aprobar_solicitudes_gestion() is True
    assert lider.puede_aprobar_anticipo_solicitud() is True
    assert lider.puede_gestionar_panel_compras() is False


def test_contrato_archivos_obligatorios():
    contrato = Contrato(
        proveedor_contratista="ACME",
        nit_proveedor="900.123.456-7",
        descripcion_servicio="x",
        obligaciones_colbeef="x",
        obligaciones_proveedor="x",
        valor=Decimal("1000.00"),
        moneda=Moneda.COP,
        plazo_cantidad=6,
        plazo_unidad=UnidadPlazo.MESES,
        renovacion_automatica=True,
        condiciones_recibido_satisfactorio="x",
        requiere_poliza=False,
        creado_por_id=1,
        correo_lider_proceso="lider@example.com",
        correo_gerencia="gerencia@example.com",
    )

    assert contrato.compania == COMPANIA_DEFAULT == "Colbeef"
    assert not contrato.archivos_obligatorios_presentes()
    assert len(contrato.archivos_obligatorios_faltantes()) == 3


def test_roles_values():
    assert set(Role.values()) == {
        "admin",
        "juridica",
        "compras",
        "solicitante",
        "anticipos",
        "lider_aprobador",
        "proyectos",
        "contabilidad",
        "tesoreria",
    }
    assert set(Moneda.values()) == {"COP", "USD", "EUR"}
    assert set(UnidadPlazo.values()) == {"dias", "dias_calendario", "meses", "anios"}


def test_tipo_precio_formas_pago():
    from app.domain.value_objects.tipo_precio import TipoPrecio

    assert TipoPrecio.MAS_IVA.label == "Más IVA"
    assert TipoPrecio.AUI.label == "AUI"
    assert TipoPrecio.NO_APLICA.label == "No aplica"
    assert set(TipoPrecio.values()) == {"mas_iva", "aui", "no_aplica"}


def test_aprobacion_gerencia_por_valor():
    from decimal import Decimal

    from app.application.services.aprobacion_gerencia import correo_aprobacion_gerencia
    from app.domain.value_objects.moneda import Moneda
    from app.infrastructure.config import settings

    diego = settings.APROBACION_DIEGO_SERRANO_EMAIL.strip()
    gerencia = (
        settings.APROBACION_GERENCIA_GENERAL_EMAIL.strip()
        or settings.GERENCIA_EMAIL.strip()
    )

    correo_bajo, etiqueta_bajo = correo_aprobacion_gerencia(Decimal("9999999.99"), Moneda.COP)
    correo_igual, _ = correo_aprobacion_gerencia(Decimal("10000000"), Moneda.COP)
    correo_alto, etiqueta_alto = correo_aprobacion_gerencia(Decimal("10000000.01"), Moneda.COP)
    correo_usd, _ = correo_aprobacion_gerencia(Decimal("100"), Moneda.USD)

    assert correo_bajo == diego
    assert "Diego Serrano" in etiqueta_bajo
    assert correo_igual == diego
    assert correo_alto == gerencia
    assert "Gerencia General" in etiqueta_alto
    assert correo_usd == gerencia


def test_tipo_archivo_obligatorios_count():
    assert len(TipoArchivo.obligatorios_radicacion()) == 3
    assert TipoArchivo.OPCIONAL not in TipoArchivo.obligatorios_radicacion()
    assert TipoArchivo.POLIZA not in TipoArchivo.obligatorios_radicacion()
    assert TipoArchivo.BORRADOR_FIRMADO not in TipoArchivo.obligatorios_radicacion()


def test_estado_contrato_y_codigo():
    from app.domain.entities.contrato import construir_codigo, normalizar_tipo_codigo
    from app.domain.value_objects.estado_contrato import EstadoContrato

    assert construir_codigo(1) == "C-0001"
    assert construir_codigo(42, "OS") == "OS-0042"
    assert construir_codigo(12345, "C") == "C-12345"
    assert normalizar_tipo_codigo("os") == "OS"
    assert set(EstadoContrato.values()) == {
        "en_proceso",
        "elaborando",
        "revision_polizas",
        "solicitud_firmas",
        "anticipo_contabilidad",
        "anticipo_tesoreria",
        "anticipo_pagado",
        "activo",
        "finalizado",
        "cierre_contabilidad",
        "cierre_tesoreria",
        "completado",
    }
    assert EstadoContrato.EN_PROCESO.label == "En proceso"
    assert EstadoContrato.ELABORANDO.label == "Elaborando contrato"


def test_calcular_fecha_fin_con_meses():
    from app.application.use_cases.contratos.radicar_solicitud import calcular_fecha_fin

    assert calcular_fecha_fin(date(2026, 1, 31), 1, UnidadPlazo.MESES) == date(2026, 3, 2)
    assert calcular_fecha_fin(date(2026, 7, 10), 30, UnidadPlazo.DIAS_CALENDARIO) == date(2026, 8, 9)
    assert calcular_fecha_fin(date(2026, 7, 10), 30, UnidadPlazo.DIAS) == date(2026, 8, 26)


def test_juridica_solo_puede_radicar_contratos():
    from app.application.use_cases.contratos.radicar_solicitud import (
        _validar_actor_y_tipo,
    )
    from app.domain.exceptions import UnauthorizedError

    juridica = User(username="j", password_hash="x", role=Role.JURIDICA)
    compras = User(username="c", password_hash="x", role=Role.COMPRAS)

    assert _validar_actor_y_tipo(juridica, "C") == "C"
    assert _validar_actor_y_tipo(compras, "OS") == "OS"
    with pytest.raises(UnauthorizedError, match="sólo puede radicar contratos"):
        _validar_actor_y_tipo(juridica, "OS")


def test_editar_contrato_preserva_inicio_original():
    from app.application.use_cases.contratos.editar_contrato import EditarContrato
    from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
    from app.domain.value_objects.estado_contrato import EstadoContrato
    from app.domain.value_objects.tipo_precio import TipoPrecio

    contrato = Contrato(
        proveedor_contratista="ACME",
        nit_proveedor="900",
        descripcion_servicio="x",
        obligaciones_colbeef="x",
        obligaciones_proveedor="x",
        valor=Decimal("1000.00"),
        moneda=Moneda.COP,
        plazo_cantidad=6,
        plazo_unidad=UnidadPlazo.MESES,
        renovacion_automatica=False,
        condiciones_recibido_satisfactorio="x",
        requiere_poliza=False,
        creado_por_id=1,
        correo_lider_proceso="l@e.com",
        correo_gerencia="g@e.com",
        id=1,
        estado=EstadoContrato.ACTIVO,
        estado_aprobacion=EstadoAprobacion.APROBADO,
    )

    class FakeRepo:
        def __init__(self, c):
            self._c = c

        def get_by_id(self, _cid):
            return self._c

        def update(self, c):
            self._c = c
            return c

    uc = EditarContrato(FakeRepo(contrato))
    juridica = User(username="j", password_hash="x", role=Role.JURIDICA)

    def editar(fi, ff):
        return uc.execute(
            actor=juridica,
            contrato_id=1,
            proveedor_contratista="ACME",
            nit_proveedor="900",
            descripcion_servicio="x",
            obligaciones_colbeef="x",
            obligaciones_proveedor="x",
            valor=Decimal("1000.00"),
            moneda=Moneda.COP,
            plazo_cantidad=6,
            plazo_unidad=UnidadPlazo.MESES,
            renovacion_automatica=False,
                condiciones_recibido_satisfactorio="x",
                requiere_poliza=False,
                tipo_precio=TipoPrecio.MAS_IVA,
                forma_pago="Sin anticipo",
                fecha_inicio=fi,
                fecha_fin=ff,
                fecha_proxima_notificacion=None,
                hora_proxima_notificacion=None,
                centro_costos="307-10 PTAR",
            )

    c1 = editar(date(2026, 1, 1), date(2026, 7, 1))
    assert c1.fecha_inicio_original == date(2026, 1, 1)
    assert c1.centro_costos == "307-10 PTAR"

    # Una prórroga cambia las fechas, pero el inicio original se conserva.
    c2 = editar(date(2026, 3, 1), date(2026, 9, 1))
    assert c2.fecha_inicio == date(2026, 3, 1)
    assert c2.fecha_inicio_original == date(2026, 1, 1)


def test_codigo_solicitud_por_tipo():
    from app.domain.entities.solicitud_gestion import construir_codigo_solicitud
    from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

    assert construir_codigo_solicitud(1, TipoSolicitudGestion.COMPRA) == "SG-0001"
    assert construir_codigo_solicitud(42, TipoSolicitudGestion.SALIDAS_ALMACEN) == "SA-0042"
    assert construir_codigo_solicitud(7, TipoSolicitudGestion.INSUMOS_SERVICIOS) == "SRV-0007"
    assert construir_codigo_solicitud(3, "salidas_almacen") == "SA-0003"
    # Consecutivos independientes: el #3 de compra y el #3 de salidas comparten número, no ID global.
    assert construir_codigo_solicitud(3, TipoSolicitudGestion.COMPRA) == "SG-0003"


def test_elaboracion_dias_habiles_y_limite():
    from datetime import datetime, timedelta

    from app.domain.entities.contrato import contar_dias_habiles, sumar_dias_habiles
    from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
    from app.domain.value_objects.estado_contrato import EstadoContrato

    # Viernes + 2 hábiles = martes (salta sábado y domingo).
    viernes = date(2026, 7, 24)
    assert sumar_dias_habiles(viernes, 2) == date(2026, 7, 28)
    # El viernes, faltan 2 días hábiles hasta el martes (el finde no infla).
    assert contar_dias_habiles(viernes, date(2026, 7, 28)) == 2
    # Ya vencido: negativo.
    assert contar_dias_habiles(date(2026, 7, 28), viernes) == -2

    def nuevo(**kw):
        base = dict(
            proveedor_contratista="ACME", nit_proveedor="900",
            descripcion_servicio="x", obligaciones_colbeef="x",
            obligaciones_proveedor="x", valor=Decimal("1000.00"),
            moneda=Moneda.COP, plazo_cantidad=6, plazo_unidad=UnidadPlazo.MESES,
            renovacion_automatica=False, condiciones_recibido_satisfactorio="x",
            requiere_poliza=False, creado_por_id=1,
            correo_lider_proceso="l@e.com", correo_gerencia="g@e.com", id=1,
        )
        base.update(kw)
        return Contrato(**base)

    # En proceso (aún sin aprobar/elaborar): no aplica elaboración.
    assert nuevo(estado=EstadoContrato.EN_PROCESO).dias_para_elaborar() is None

    # En estado 'elaborando': cuenta días hábiles hasta la fecha límite (override).
    limite = date.today() + timedelta(days=5)
    aprobado = nuevo(
        estado=EstadoContrato.ELABORANDO,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        aprobado_gerencia_at=datetime.now(),
        fecha_limite_elaboracion=limite,
    )
    assert aprobado.dias_para_elaborar() == contar_dias_habiles(date.today(), limite)

    # Ya activo: la elaboración dejó de aplicar.
    assert nuevo(
        estado=EstadoContrato.ACTIVO,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        aprobado_gerencia_at=datetime.now(),
    ).dias_para_elaborar() is None
