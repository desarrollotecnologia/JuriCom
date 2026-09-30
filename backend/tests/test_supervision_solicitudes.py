"""Un visor (p. ej. mantenimiento@colbeef.com) ve las solicitudes de los
solicitantes que supervisa: en el listado y en el detalle/trazabilidad."""

import pytest

from app.application.use_cases.solicitudes_gestion.get_solicitud_gestion import (
    GetSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.listar_solicitudes_gestion import (
    ListarSolicitudesGestion,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

VISOR_EMAIL = "mantenimiento@colbeef.com"
SUP_EMAIL = "planeador.colbeef@soatsas.com"
OTRO_EMAIL = "ajeno@colbeef.com"


def _sol(id, creador_id, email, estado=EstadoSolicitudGestion.SOLICITUD):
    return SolicitudGestion(
        tipo=TipoSolicitudGestion.COMPRA,
        titulo=f"S{id}",
        creado_por_id=creador_id,
        creado_por_email=email,
        estado=estado,
        id=id,
    )


class FakeRepo:
    def __init__(self, solicitudes):
        self._s = {s.id: s for s in solicitudes}

    def list_all(self, *, creador_id=None, tipo=None, query=None, **kw):
        vals = list(self._s.values())
        if creador_id is not None:
            vals = [s for s in vals if s.creado_por_id == creador_id]
        return vals

    def get_by_id(self, solicitud_id):
        return self._s.get(solicitud_id)

    def get_historial(self, solicitud_id):
        return ["h1", "h2"]


def _visor():
    return User(username="manto", password_hash="x", role=Role.SOLICITANTE, id=57, email=VISOR_EMAIL)


def _repo():
    # id 2 y 3 en estado terminal (cancelado): un solicitante normal NO podría verlas.
    # Así probamos que la supervisión da acceso más allá de lo normal.
    return FakeRepo([
        _sol(1, 57, VISOR_EMAIL),
        _sol(2, 66, SUP_EMAIL, estado=EstadoSolicitudGestion.CANCELADO),
        _sol(3, 99, OTRO_EMAIL, estado=EstadoSolicitudGestion.CANCELADO),
    ])


def test_listado_incluye_propias_y_supervisadas_no_ajenas():
    res = ListarSolicitudesGestion(_repo()).execute(_visor())
    ids = sorted(s.id for s in res)
    assert ids == [1, 2]  # ve la propia y la supervisada, no la ajena


def test_detalle_y_trazabilidad_de_supervisada_permitido():
    caso = GetSolicitudGestion(_repo())
    assert caso.execute(_visor(), 2).id == 2
    assert caso.get_historial(_visor(), 2) == ["h1", "h2"]


def test_detalle_de_ajena_denegado():
    with pytest.raises(UnauthorizedError):
        GetSolicitudGestion(_repo()).execute(_visor(), 3)
