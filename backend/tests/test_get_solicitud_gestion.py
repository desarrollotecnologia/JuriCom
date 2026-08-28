"""Jurídica ve SRV solo si está vinculada a un contrato/OT."""

from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.get_solicitud_gestion import (
    GetSolicitudGestion,
)
from app.domain.exceptions import UnauthorizedError


class FakeRepo:
    def __init__(self, solicitud):
        self._solicitud = solicitud

    def get_by_id(self, _id):
        return self._solicitud


def _actor(rol):
    return SimpleNamespace(
        is_admin=lambda: rol == "admin",
        is_juridica=lambda: rol == "juridica",
        ve_solo_propias_solicitudes_gestion=lambda: False,
        is_lider_aprobador=lambda: False,
    )


def test_juridica_ve_srv_vinculada():
    uc = GetSolicitudGestion(FakeRepo(SimpleNamespace(id=1, contrato_id=9, creado_por_id=3)))
    assert uc.execute(_actor("juridica"), 1).id == 1


def test_juridica_no_ve_srv_sin_contrato():
    uc = GetSolicitudGestion(FakeRepo(SimpleNamespace(id=1, contrato_id=None, creado_por_id=3)))
    with pytest.raises(UnauthorizedError):
        uc.execute(_actor("juridica"), 1)
