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
    }
    assert set(Moneda.values()) == {"COP", "USD", "EUR"}
    assert set(UnidadPlazo.values()) == {"dias", "meses", "anios"}


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
    assert set(EstadoContrato.values()) == {"en_proceso", "activo", "finalizado"}
    assert EstadoContrato.EN_PROCESO.label == "En proceso"


def test_calcular_fecha_fin_con_meses():
    from app.application.use_cases.contratos.radicar_solicitud import calcular_fecha_fin

    assert calcular_fecha_fin(date(2026, 1, 31), 1, UnidadPlazo.MESES) == date(2026, 2, 28)
    assert calcular_fecha_fin(date(2026, 7, 10), 30, UnidadPlazo.DIAS) == date(2026, 8, 9)


def test_codigo_solicitud_por_tipo():
    from app.domain.entities.solicitud_gestion import construir_codigo_solicitud
    from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

    assert construir_codigo_solicitud(1, TipoSolicitudGestion.COMPRA) == "SG-0001"
    assert construir_codigo_solicitud(42, TipoSolicitudGestion.SALIDAS_ALMACEN) == "SA-0042"
    assert construir_codigo_solicitud(7, TipoSolicitudGestion.INSUMOS_SERVICIOS) == "SRV-0007"
    assert construir_codigo_solicitud(3, "salidas_almacen") == "SA-0003"
    # Consecutivos independientes: el #3 de compra y el #3 de salidas comparten número, no ID global.
    assert construir_codigo_solicitud(3, TipoSolicitudGestion.COMPRA) == "SG-0003"
