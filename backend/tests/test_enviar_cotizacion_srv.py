"""Cotizaciones de servicios: valor/anticipo por archivo y Diego Financiera."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.services.lideres_colbeef import (
    DIEGO_FINANCIERA_ID,
    DIEGO_FINANCIERA_LABEL,
)
from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
    _aplicar_datos_economicos_srv,
    _copiar_propuesta_a_solicitud,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


def _entrada(**kwargs):
    defaults = dict(
        nombre_original="c.pdf",
        mime_type="application/pdf",
        contenido=b"x",
        valor_cotizacion=Decimal("7000000"),
        requiere_anticipo=False,
        propuesta=False,
    )
    defaults.update(kwargs)
    return ArchivoEntradaSolicitud(**defaults)


def test_exige_valor_en_cada_cotizacion():
    with pytest.raises(ValueError, match="valor"):
        _aplicar_datos_economicos_srv(
            [_entrada(valor_cotizacion=None, propuesta=True)]
        )


def test_no_exige_propuesta_al_enviar():
    _aplicar_datos_economicos_srv(
        [_entrada(propuesta=False), _entrada(propuesta=False)]
    )


def test_calcula_monto_anticipo():
    e = _entrada(
        propuesta=True,
        requiere_anticipo=True,
        porcentaje_anticipo=Decimal("30"),
    )
    _aplicar_datos_economicos_srv([e])
    assert e.monto_anticipo == Decimal("2100000.00")


def test_copia_propuesta_a_solicitud_y_clasifica_ot():
    solicitud = SimpleNamespace(
        tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
        valor_tramite_oc=None,
        clasificacion_documento_servicio="",
        gestion_valor_registrada=False,
        requiere_anticipo=False,
        porcentaje_anticipo=None,
        monto_anticipo=None,
        lider_anticipo_id="x",
        lider_anticipo_label="y",
        observaciones_anticipo="z",
    )
    _copiar_propuesta_a_solicitud(
        solicitud,
        _entrada(valor_cotizacion=Decimal("7000000"), propuesta=True),
    )
    assert solicitud.valor_tramite_oc == Decimal("7000000")
    assert solicitud.clasificacion_documento_servicio == "orden_trabajo"
    assert solicitud.gestion_valor_registrada is True
    assert solicitud.requiere_anticipo is False
    assert solicitud.lider_anticipo_id == ""


def test_usd_no_usa_umbrales_cop():
    solicitud = SimpleNamespace(
        valor_tramite_oc=None,
        clasificacion_documento_servicio="",
        gestion_valor_registrada=False,
        requiere_anticipo=False,
        porcentaje_anticipo=None,
        monto_anticipo=None,
        lider_anticipo_id="",
        lider_anticipo_label="",
        observaciones_anticipo="",
    )
    _copiar_propuesta_a_solicitud(
        solicitud,
        _entrada(
            valor_cotizacion=Decimal("7000000"),
            moneda_cotizacion="USD",
            propuesta=True,
        ),
    )
    assert solicitud.valor_tramite_oc == Decimal("7000000")
    assert solicitud.clasificacion_documento_servicio == ""
    assert solicitud.gestion_valor_registrada is True


def test_diego_constantes():
    assert DIEGO_FINANCIERA_ID == "13542263"
    assert "DIEGO" in DIEGO_FINANCIERA_LABEL
