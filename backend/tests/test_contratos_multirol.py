"""Jurídica/Admin con rol extra Supervisor o Compras siguen viendo todos los contratos aprobados."""

from types import SimpleNamespace

import pytest

from app.application.use_cases.contratos.buscar_contratos import BuscarContratos
from app.application.use_cases.contratos.get_contrato import GetContrato
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion


def _actor(*roles, actor_id=5):
    return SimpleNamespace(
        id=actor_id,
        **{f"is_{r}": (lambda r=r: r in roles) for r in (
            "admin", "juridica", "compras", "solicitante", "contabilidad", "tesoreria"
        )},
    )


class FakeRepo:
    def __init__(self, contrato):
        self.contrato = contrato
        self.search_kwargs = None

    def get_by_id(self, _id):
        return self.contrato

    def search(self, **kwargs):
        self.search_kwargs = kwargs
        return [self.contrato]


def _contrato(aprobacion=EstadoAprobacion.APROBADO):
    return SimpleNamespace(id=34, supervisor_id=99, creado_por_id=99, estado_aprobacion=aprobacion)


def test_juridica_supervisor_ve_contrato_ajeno():
    assert GetContrato(FakeRepo(_contrato())).execute(_actor("solicitante", "juridica"), 34).id == 34


def test_juridica_supervisor_lista_sin_filtro_de_supervisor():
    repo = FakeRepo(_contrato())
    BuscarContratos(repo).execute(_actor("solicitante", "juridica"))
    assert repo.search_kwargs["supervisor_id"] is None
    assert repo.search_kwargs["solo_aprobados"] is True


def test_supervisor_solo_sigue_restringido():
    with pytest.raises(UnauthorizedError):
        GetContrato(FakeRepo(_contrato())).execute(_actor("solicitante"), 34)


def test_juridica_no_ve_contrato_sin_aprobar():
    with pytest.raises(UnauthorizedError):
        GetContrato(FakeRepo(_contrato(EstadoAprobacion.PENDIENTE_LIDER))).execute(
            _actor("solicitante", "juridica"), 34
        )
