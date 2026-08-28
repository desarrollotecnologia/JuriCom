"""Regla de activación: exige contrato firmado, NO exige póliza.

La póliza la sube Jurídica/Gerencia durante la elaboración, por eso no
debe bloquear la activación aunque `requiere_poliza` sea True.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.application.use_cases.contratos.cambiar_estado import CambiarEstadoContrato
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.unidad_plazo import UnidadPlazo


class FakeRepo:
    def __init__(self, contrato):
        self._contrato = contrato

    def get_by_id(self, _id):
        return self._contrato

    def update(self, contrato):
        return contrato


def _actor():
    return SimpleNamespace(
        id=1,
        is_admin=lambda: False,
        is_juridica=lambda: True,
        is_compras=lambda: False,
        is_solicitante=lambda: False,
    )


def _contrato(tiene_borrador: bool, requiere_poliza: bool):
    return SimpleNamespace(
        id=10,
        estado=EstadoContrato.ELABORANDO,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        requiere_poliza=requiere_poliza,
        tiene_borrador=lambda: tiene_borrador,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=30),
        fecha_inicio_original=None,
        plazo_cantidad=1,
        plazo_unidad=UnidadPlazo.MESES,
        fecha_proxima_notificacion=date.today(),
        hora_proxima_notificacion=None,
        aprobado_gerencia_at=None,
    )


def test_activar_sin_contrato_firmado_falla():
    uc = CambiarEstadoContrato(FakeRepo(_contrato(tiene_borrador=False, requiere_poliza=True)))
    with pytest.raises(ValueError):
        uc.execute(_actor(), 10, EstadoContrato.ACTIVO)


def test_activar_con_contrato_firmado_ok_aunque_falte_poliza():
    # requiere_poliza=True pero SIN póliza: igual debe activar (la póliza va en elaboración).
    c = _contrato(tiene_borrador=True, requiere_poliza=True)
    uc = CambiarEstadoContrato(FakeRepo(c))
    result = uc.execute(_actor(), 10, EstadoContrato.ACTIVO)
    assert result.estado == EstadoContrato.ACTIVO


def test_pasar_a_revision_polizas_y_solicitud_firmas():
    for nuevo in (EstadoContrato.REVISION_POLIZAS, EstadoContrato.SOLICITUD_FIRMAS):
        c = _contrato(tiene_borrador=False, requiere_poliza=False)
        uc = CambiarEstadoContrato(FakeRepo(c))
        result = uc.execute(_actor(), 10, nuevo)
        assert result.estado == nuevo


def test_pasar_a_elaborando_arranca_contador():
    # Al entrar en ELABORANDO se fija aprobado_gerencia_at (inicio del plazo 2 días).
    c = _contrato(tiene_borrador=False, requiere_poliza=False)
    c.estado = EstadoContrato.EN_PROCESO
    uc = CambiarEstadoContrato(FakeRepo(c))
    result = uc.execute(_actor(), 10, EstadoContrato.ELABORANDO)
    assert result.estado == EstadoContrato.ELABORANDO
    assert result.aprobado_gerencia_at is not None


def test_no_se_puede_cambiar_estado_durante_anticipo():
    # Mientras el anticipo está en Contabilidad/Tesorería, Jurídica no puede sacar
    # el contrato del sub-flujo cambiando el estado a mano.
    for estado_anticipo in (
        EstadoContrato.ANTICIPO_CONTABILIDAD,
        EstadoContrato.ANTICIPO_TESORERIA,
    ):
        c = _contrato(tiene_borrador=True, requiere_poliza=False)
        c.estado = estado_anticipo
        uc = CambiarEstadoContrato(FakeRepo(c))
        for destino in (
            EstadoContrato.ELABORANDO,
            EstadoContrato.SOLICITUD_FIRMAS,
            EstadoContrato.ACTIVO,
        ):
            with pytest.raises(ValueError):
                uc.execute(_actor(), 10, destino)
        # El estado no se modifica.
        assert c.estado == estado_anticipo
