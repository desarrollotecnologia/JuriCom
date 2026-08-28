"""Flujo del anticipo del contrato: Jurídica → Contabilidad → Tesorería → Jurídica.

Verifica transiciones de estado, permisos por rol y el gating que impide
activar el contrato mientras el anticipo no haya sido pagado por Tesorería.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.application.use_cases.contratos.anticipo_contrato import (
    ConfirmarPagoTesoreria,
    EnviarAnticipoContabilidad,
    GestionarAnticipoContabilidad,
)
from app.application.use_cases.contratos.cambiar_estado import CambiarEstadoContrato
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.roles import Role
from app.domain.value_objects.unidad_plazo import UnidadPlazo


class FakeRepo:
    def __init__(self, contrato):
        self._contrato = contrato

    def get_by_id(self, _id):
        return self._contrato

    def update(self, contrato):
        return contrato


def _user(role: Role) -> User:
    return User(username=role.value, password_hash="x", role=role, id=1)


def _contrato(**over):
    base = dict(
        id=10,
        estado=EstadoContrato.SOLICITUD_FIRMAS,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        requiere_anticipo=True,
        anticipo_pagado=False,
        requiere_poliza=False,
        tiene_poliza=lambda: True,
        tiene_borrador=lambda: True,
        fecha_inicio=date.today(),
        fecha_fin=date.today() + timedelta(days=30),
        fecha_inicio_original=None,
        plazo_cantidad=1,
        plazo_unidad=UnidadPlazo.MESES,
        fecha_proxima_notificacion=date.today(),
        hora_proxima_notificacion=None,
        aprobado_gerencia_at=None,
    )
    base.update(over)
    return SimpleNamespace(**base)


def test_flujo_completo_anticipo():
    c = _contrato()
    repo = FakeRepo(c)

    EnviarAnticipoContabilidad(repo).execute(_user(Role.JURIDICA), 10)
    assert c.estado == EstadoContrato.ANTICIPO_CONTABILIDAD

    GestionarAnticipoContabilidad(repo).execute(_user(Role.CONTABILIDAD), 10)
    assert c.estado == EstadoContrato.ANTICIPO_TESORERIA

    ConfirmarPagoTesoreria(repo).execute(_user(Role.TESORERIA), 10)
    assert c.anticipo_pagado is True
    # Tras el pago, el contrato pasa a ANTICIPO_PAGADO (avisa a Jurídica para activar).
    assert c.estado == EstadoContrato.ANTICIPO_PAGADO


def test_no_activa_sin_pago_de_tesoreria():
    c = _contrato(estado=EstadoContrato.SOLICITUD_FIRMAS, anticipo_pagado=False)
    uc = CambiarEstadoContrato(FakeRepo(c))
    with pytest.raises(ValueError):
        uc.execute(_user(Role.JURIDICA), 10, EstadoContrato.ACTIVO)


def test_activa_tras_pago_de_tesoreria():
    c = _contrato(estado=EstadoContrato.SOLICITUD_FIRMAS, anticipo_pagado=True)
    uc = CambiarEstadoContrato(FakeRepo(c))
    result = uc.execute(_user(Role.JURIDICA), 10, EstadoContrato.ACTIVO)
    assert result.estado == EstadoContrato.ACTIVO


def test_sin_anticipo_activa_normal():
    c = _contrato(requiere_anticipo=False, estado=EstadoContrato.ELABORANDO)
    uc = CambiarEstadoContrato(FakeRepo(c))
    result = uc.execute(_user(Role.JURIDICA), 10, EstadoContrato.ACTIVO)
    assert result.estado == EstadoContrato.ACTIVO


def test_permisos_por_rol():
    c = _contrato()
    repo = FakeRepo(c)
    # Contabilidad no puede iniciar el envío (eso lo hace Jurídica).
    with pytest.raises(UnauthorizedError):
        EnviarAnticipoContabilidad(repo).execute(_user(Role.CONTABILIDAD), 10)
    # Tesorería no puede gestionar la etapa de Contabilidad.
    c.estado = EstadoContrato.ANTICIPO_CONTABILIDAD
    with pytest.raises(UnauthorizedError):
        GestionarAnticipoContabilidad(repo).execute(_user(Role.TESORERIA), 10)
    # Contabilidad no puede confirmar el pago.
    c.estado = EstadoContrato.ANTICIPO_TESORERIA
    with pytest.raises(UnauthorizedError):
        ConfirmarPagoTesoreria(repo).execute(_user(Role.CONTABILIDAD), 10)


def test_no_reenvia_si_ya_pagado():
    c = _contrato(anticipo_pagado=True)
    with pytest.raises(ValueError):
        EnviarAnticipoContabilidad(FakeRepo(c)).execute(_user(Role.JURIDICA), 10)


def test_contrato_sin_anticipo_no_se_envia():
    c = _contrato(requiere_anticipo=False)
    with pytest.raises(ValueError):
        EnviarAnticipoContabilidad(FakeRepo(c)).execute(_user(Role.JURIDICA), 10)


def test_no_envia_sin_contrato_firmado():
    c = _contrato(tiene_borrador=lambda: False)
    with pytest.raises(ValueError):
        EnviarAnticipoContabilidad(FakeRepo(c)).execute(_user(Role.JURIDICA), 10)


def test_no_envia_sin_poliza_cuando_se_requiere():
    c = _contrato(requiere_poliza=True, tiene_poliza=lambda: False)
    with pytest.raises(ValueError):
        EnviarAnticipoContabilidad(FakeRepo(c)).execute(_user(Role.JURIDICA), 10)


def test_envia_con_poliza_y_firmado_ok():
    c = _contrato(requiere_poliza=True, tiene_poliza=lambda: True, tiene_borrador=lambda: True)
    EnviarAnticipoContabilidad(FakeRepo(c)).execute(_user(Role.JURIDICA), 10)
    assert c.estado == EstadoContrato.ANTICIPO_CONTABILIDAD
