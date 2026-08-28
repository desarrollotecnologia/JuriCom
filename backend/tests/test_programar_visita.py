"""Programar visita antes de cotizar (cuando el solicitante marca "requiere visita").

Flujo normal:  Primera aprobación → (Compras toma) Programar visita → Cotización.
Flujo comité:  Revisión Proyectos → Programar visita → Cotización (Proyectos).
"""

from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.gestionar_solicitud_panel import (
    GestionarSolicitudPanel,
)
from app.application.use_cases.solicitudes_gestion.guardar_gestion_servicios_solicitud import (
    GuardarGestionServiciosSolicitud,
)
from app.application.use_cases.solicitudes_gestion.responder_revision_proyectos import (
    ResponderRevisionProyectos,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class FakeStorage:
    def save(self, *, contenido, nombre_original, mime_type, subcarpeta=""):
        return SimpleNamespace(
            nombre_original=nombre_original,
            ruta=f"{subcarpeta}/{nombre_original}",
            mime_type=mime_type,
            tamano_bytes=len(contenido or b""),
        )


class FakeRepo:
    def __init__(self, solicitud):
        self.s = solicitud
        self.observaciones = []
        self.historial = []
        self.visitas = None
        self._oid = 0

    def get_by_id(self, solicitud_id):
        return self.s

    def update(self, solicitud):
        self.s = solicitud
        return solicitud

    def registrar_historial(self, solicitud_id, etapa, *, usuario_id=None, comentario=""):
        self.historial.append(SimpleNamespace(etapa=etapa, comentario=comentario))

    def replace_visitas_programadas(self, solicitud_id, visitas):
        self.visitas = visitas

    def add_observacion(self, solicitud_id, observacion):
        self._oid += 1
        observacion.id = self._oid
        self.observaciones.append(observacion)
        return observacion

    def get_observaciones(self, solicitud_id):
        return self.observaciones

    def get_observacion_by_id(self, observacion_id):
        return next((o for o in self.observaciones if o.id == observacion_id), None)


def _user(role, uid, username="u"):
    return User(username=username, password_hash="x", role=role, id=uid)


def _srv(estado, *, comite=False):
    return SolicitudGestion(
        tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
        titulo="Servicio X",
        creado_por_id=10,
        requiere_visita=True,
        requiere_comite_tecnico=comite,
        estado=estado,
    )


_VISITAS_JSON = (
    '[{"proveedor_visita":"ACME SAS","fecha_visita":"2026-09-01","hora_visita":"10:00"}]'
)


def test_normal_toma_gestion_va_a_programar_visita():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.PRIMERA_APROBACION))
    compras = _user(Role.COMPRAS, 7, "compras")
    res = GestionarSolicitudPanel(repo).execute(compras, 1)
    assert res.estado == EstadoSolicitudGestion.PROGRAMACION_VISITA
    assert res.gestor_id == 7


def test_normal_confirmar_visita_pasa_a_cotizacion():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.PROGRAMACION_VISITA))
    repo.s.gestor_id = 7
    compras = _user(Role.COMPRAS, 7, "compras")
    res = GuardarGestionServiciosSolicitud(repo, FakeStorage()).execute(
        compras, 1, visitas_json=_VISITAS_JSON
    )
    assert res.estado == EstadoSolicitudGestion.COTIZACION
    assert repo.visitas and repo.visitas[0].proveedor_visita == "ACME SAS"
    assert repo.visitas[0].programador_visita == "compras"
    assert repo.visitas[0].rol_programador == "compras"


def test_visita_requiere_al_menos_una():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.PROGRAMACION_VISITA))
    repo.s.gestor_id = 7
    compras = _user(Role.COMPRAS, 7, "compras")
    with pytest.raises(ValueError, match="al menos una visita"):
        GuardarGestionServiciosSolicitud(repo, FakeStorage()).execute(
            compras, 1, visitas_json="[]"
        )


def test_comite_revision_con_visita_va_a_programar_visita():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.REVISION_PROYECTOS, comite=True))
    proy = _user(Role.PROYECTOS, 55, "proy")
    res = ResponderRevisionProyectos(repo, FakeStorage()).execute(
        proy, 1, titulo="Reescrito"
    )
    assert res.estado == EstadoSolicitudGestion.PROGRAMACION_VISITA


def test_comite_visita_proyectos_pasa_a_cotizacion_proyectos():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.PROGRAMACION_VISITA, comite=True))
    proy = _user(Role.PROYECTOS, 55, "proy")
    res = GuardarGestionServiciosSolicitud(repo, FakeStorage()).execute(
        proy, 1, visitas_json=_VISITAS_JSON
    )
    assert res.estado == EstadoSolicitudGestion.COTIZACION_PROYECTOS
    assert res.visita_proyectos_hecha is True
    assert repo.visitas and repo.visitas[0].rol_programador == "proyectos"


def test_comite_segunda_visita_la_agenda_compras():
    # Tras la visita de Proyectos (visita_proyectos_hecha=True), Compras agenda la suya
    # y se conserva la visita previa de Proyectos (diferenciadas por rol).
    from app.domain.entities.solicitud_gestion import SolicitudGestionVisitaProgramada

    repo = FakeRepo(_srv(EstadoSolicitudGestion.PROGRAMACION_VISITA, comite=True))
    repo.s.visita_proyectos_hecha = True
    repo.s.visitas_programadas = [
        SolicitudGestionVisitaProgramada(
            programador_visita="proy",
            rol_programador="proyectos",
            proveedor_visita="PREVIA SAS",
        )
    ]
    compras = _user(Role.COMPRAS, 7, "compras")
    res = GuardarGestionServiciosSolicitud(repo, FakeStorage()).execute(
        compras, 1, visitas_json=_VISITAS_JSON
    )
    assert res.estado == EstadoSolicitudGestion.COTIZACION
    roles = {v.rol_programador for v in repo.visitas}
    assert roles == {"proyectos", "compras"}


def test_comite_segunda_visita_no_la_agenda_proyectos():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.PROGRAMACION_VISITA, comite=True))
    repo.s.visita_proyectos_hecha = True
    proy = _user(Role.PROYECTOS, 55, "proy")
    with pytest.raises(Exception):
        GuardarGestionServiciosSolicitud(repo, FakeStorage()).execute(
            proy, 1, visitas_json=_VISITAS_JSON
        )
