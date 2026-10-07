"""Especialistas de mantenimiento: ven las SRV en comité técnico (sin votar)."""

import pytest

from app.application.use_cases.solicitudes_gestion.get_solicitud_gestion import (
    GetSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.listar_solicitudes_gestion import (
    ListarSolicitudesGestion,
)
from app.application.use_cases.solicitudes_gestion.resolver_comite_tecnico import (
    ResolverComiteTecnico,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


def _srv(sid, estado, comite=True):
    return SolicitudGestion(
        id=sid,
        tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
        titulo=f"SRV {sid}",
        creado_por_id=10,
        creado_por_email="otro@colbeef.com",
        requiere_comite_tecnico=comite,
        estado=estado,
    )


class FakeRepo:
    def __init__(self, items):
        self.items = {s.id: s for s in items}

    def list_all(self, creador_id=None, tipo=None, query=None, **_):
        return [s for s in self.items.values() if creador_id is None or s.creado_por_id == creador_id]

    def get_by_id(self, sid):
        return self.items.get(sid)


def _user(email, uid=50):
    return User(username=email, password_hash="x", role=Role.SOLICITANTE, id=uid, email=email)


REPO = FakeRepo(
    [
        _srv(1, EstadoSolicitudGestion.COMITE),
        _srv(2, EstadoSolicitudGestion.COMITE, comite=False),
        _srv(3, EstadoSolicitudGestion.EN_APROBACION),
    ]
)


def test_mantenimiento_ve_solo_srv_en_comite():
    ids = [s.id for s in ListarSolicitudesGestion(REPO).execute(_user("aux.mantenimiento@colbeef.com"))]
    assert ids == [1]
    assert GetSolicitudGestion(REPO).execute(_user("aux.mantenimiento@colbeef.com"), 1).id == 1


def test_solicitante_comun_no_ve_comite_ajeno():
    assert ListarSolicitudesGestion(REPO).execute(_user("siso@colbeef.com")) == []


def test_miembro_comite_no_puede_votar():
    with pytest.raises(UnauthorizedError):
        ResolverComiteTecnico(REPO).aceptar(_user("mantenimiento@colbeef.com"), 1)
