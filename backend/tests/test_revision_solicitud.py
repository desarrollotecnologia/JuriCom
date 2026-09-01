"""Reglas del estado 'revisión' en la primera aprobación (aprobador <-> solicitante)."""

from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.responder_revision_solicitud import (
    ResponderRevisionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.solicitar_revision_solicitud import (
    SolicitarRevisionSolicitud,
)
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class FakeRepo:
    def __init__(self, solicitud):
        self._s = solicitud
        self.historial = []
        self.observaciones = []

    def get_by_id(self, _id):
        return self._s

    def update(self, solicitud):
        self._s = solicitud
        return solicitud

    def registrar_historial(self, solicitud_id, etapa, *, usuario_id=None, comentario=""):
        self.historial.append((etapa, comentario))

    def add_observacion(self, solicitud_id, observacion):
        observacion.id = len(self.observaciones) + 1
        self.observaciones.append(observacion)
        return observacion

    def get_observacion_by_id(self, obs_id):
        return next((o for o in self.observaciones if o.id == obs_id), None)


def _actor(*, rol, actor_id=1):
    return SimpleNamespace(
        id=actor_id,
        username=f"user{actor_id}",
        role=SimpleNamespace(value=rol),
        is_admin=lambda: rol == "admin",
        is_juridica=lambda: rol == "juridica",
        is_lider_aprobador=lambda: rol == "lider_aprobador",
        puede_aprobar_solicitudes_gestion=lambda: rol in ("admin", "lider_aprobador"),
        ve_solo_propias_solicitudes_gestion=lambda: rol == "solicitante",
        solicitud_asignada_a_lider=lambda s: True,
    )


def _solicitud(estado=EstadoSolicitudGestion.SOLICITUD, creado_por_id=7):
    return SimpleNamespace(
        id=10,
        estado=estado,
        tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
        creado_por_id=creado_por_id,
        titulo="Original",
        proveedor_sugerido="",
        descripcion_servicio="",
        descripcion_servicio_texto="",
        observaciones="",
        observaciones_texto="",
        centro_costo_area="CC-1",
    )


# --- Solicitar ajustes (aprobador) ---

def test_aprobador_devuelve_a_revision():
    repo = FakeRepo(_solicitud())
    s = SolicitarRevisionSolicitud(repo).execute(
        _actor(rol="admin"), 10, observacion_texto="Falta la ficha técnica"
    )
    assert s.estado == EstadoSolicitudGestion.REVISION
    assert repo.historial[-1][0] == EstadoSolicitudGestion.REVISION
    assert repo.observaciones  # quedó el comentario del aprobador


def test_no_aprobador_no_puede_devolver():
    repo = FakeRepo(_solicitud())
    with pytest.raises(UnauthorizedError):
        SolicitarRevisionSolicitud(repo).execute(
            _actor(rol="solicitante", actor_id=7), 10, observacion_texto="x"
        )


def test_mensaje_obligatorio_al_devolver():
    repo = FakeRepo(_solicitud())
    with pytest.raises(ValueError):
        SolicitarRevisionSolicitud(repo).execute(_actor(rol="admin"), 10)


def test_solo_en_primera_aprobacion():
    repo = FakeRepo(_solicitud(estado=EstadoSolicitudGestion.EN_APROBACION))
    with pytest.raises(ValueError):
        SolicitarRevisionSolicitud(repo).execute(
            _actor(rol="admin"), 10, observacion_texto="x"
        )


# --- Responder ajustes (solicitante) ---

def test_solicitante_responde_y_reenvia():
    repo = FakeRepo(_solicitud(estado=EstadoSolicitudGestion.REVISION, creado_por_id=7))
    s = ResponderRevisionSolicitud(repo).execute(
        _actor(rol="solicitante", actor_id=7),
        10,
        observacion_texto="Ya adjunté todo",
        titulo="Servicio corregido",
        proveedor_sugerido="Proveedor X",
    )
    assert s.estado == EstadoSolicitudGestion.SOLICITUD
    assert s.titulo == "Servicio corregido"
    assert s.proveedor_sugerido == "Proveedor X"
    assert repo.historial[-1][0] == EstadoSolicitudGestion.SOLICITUD


def test_no_creador_no_puede_responder():
    repo = FakeRepo(_solicitud(estado=EstadoSolicitudGestion.REVISION, creado_por_id=7))
    with pytest.raises(UnauthorizedError):
        ResponderRevisionSolicitud(repo).execute(
            _actor(rol="solicitante", actor_id=99), 10, observacion_texto="x"
        )


def test_solo_responde_si_esta_en_revision():
    repo = FakeRepo(_solicitud(estado=EstadoSolicitudGestion.SOLICITUD, creado_por_id=7))
    with pytest.raises(ValueError):
        ResponderRevisionSolicitud(repo).execute(
            _actor(rol="solicitante", actor_id=7), 10, observacion_texto="x"
        )
