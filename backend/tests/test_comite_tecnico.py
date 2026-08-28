"""Flujo comité técnico (nuevo orden):

SOLICITUD → PRIMERA APROBACIÓN → REVISIÓN PROYECTOS (reescribe) →
COTIZACIÓN PROYECTOS → COTIZACIÓN COMPRAS → MESA TÉCNICA (comité) →
SEGUNDA APROBACIÓN (Diego) → GESTIÓN DE COMPRAS.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_proyectos import (
    EnviarCotizacionProyectos,
)
from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
    EnviarCotizacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.resolver_aprobacion_solicitud import (
    ResolverAprobacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.resolver_comite_tecnico import (
    ResolverComiteTecnico,
)
from app.application.use_cases.solicitudes_gestion.responder_revision_proyectos import (
    ResponderRevisionProyectos,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
)
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
    def __init__(self, solicitud: SolicitudGestion):
        self.s = solicitud
        self.archivos: list[SolicitudGestionArchivo] = []
        self.observaciones: list = []
        self.historial: list = []
        self._aid = 0
        self._oid = 0

    def get_by_id(self, solicitud_id):
        return self.s

    def update(self, solicitud):
        self.s = solicitud
        return solicitud

    def registrar_historial(self, solicitud_id, etapa, *, usuario_id=None, comentario=""):
        h = SimpleNamespace(etapa=etapa, usuario_id=usuario_id, comentario=comentario)
        self.historial.append(h)
        return h

    def get_historial(self, solicitud_id):
        return self.historial

    def add_archivos(self, solicitud_id, archivos, observacion_id=None):
        ids = []
        for a in archivos:
            self._aid += 1
            a.id = self._aid
            self.archivos.append(a)
            ids.append(self._aid)
        return ids

    def count_archivos_categoria(self, solicitud_id, categoria):
        return sum(1 for a in self.archivos if a.categoria == categoria)

    def add_observacion(self, solicitud_id, observacion):
        self._oid += 1
        observacion.id = self._oid
        self.observaciones.append(observacion)
        return observacion

    def get_observacion_by_id(self, observacion_id):
        return next((o for o in self.observaciones if o.id == observacion_id), None)

    def link_archivos_observacion(self, observacion_id, archivo_ids):
        pass

    def marcar_cotizacion_elegida(self, solicitud_id, archivo_id):
        return next(a for a in self.archivos if a.id == archivo_id)

    def replace_visitas_programadas(self, solicitud_id, visitas):
        pass

    def get_observaciones(self, solicitud_id):
        return self.observaciones

    def update_observacion_contenido(self, observacion_id, contenido):
        pass


def _user(role, uid, username="u"):
    return User(username=username, password_hash="x", role=role, id=uid)


def _srv(estado):
    return SolicitudGestion(
        tipo=TipoSolicitudGestion.INSUMOS_SERVICIOS,
        titulo="Servicio X",
        creado_por_id=10,
        requiere_comite_tecnico=True,
        estado=estado,
    )


def _cot():
    return ArchivoEntradaSolicitud(
        nombre_original="c.pdf",
        mime_type="application/pdf",
        contenido=b"x",
        valor_cotizacion=Decimal("7000000"),
        propuesta=False,
    )


def test_primera_aprobacion_comite_va_a_revision_proyectos():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.SOLICITUD))
    admin = _user(Role.ADMIN, 1, "admin")
    res = ResolverAprobacionSolicitud(repo).aprobar(admin, 1)
    assert res.estado == EstadoSolicitudGestion.REVISION_PROYECTOS


def test_proyectos_revisa_y_pasa_a_cotizacion():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.REVISION_PROYECTOS))
    proy = _user(Role.PROYECTOS, 55, "proy")
    res = ResponderRevisionProyectos(repo, FakeStorage()).execute(
        proy, 1, titulo="Servicio reescrito por Proyectos"
    )
    assert res.estado == EstadoSolicitudGestion.COTIZACION_PROYECTOS
    assert res.titulo == "Servicio reescrito por Proyectos"
    assert res.proyectista_id == 55


def test_proyectos_no_cotiza_en_revision():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.REVISION_PROYECTOS))
    proy = _user(Role.PROYECTOS, 55, "proy")
    with pytest.raises(ValueError, match="Cotización \\(Proyectos\\)"):
        EnviarCotizacionProyectos(repo, FakeStorage()).execute(
            proy, 1, cotizaciones=[_cot()], enviar=True
        )


def test_proyectos_cotiza_y_envia_a_compras():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.COTIZACION_PROYECTOS))
    proy = _user(Role.PROYECTOS, 55, "proy")
    res = EnviarCotizacionProyectos(repo, FakeStorage()).execute(
        proy, 1, cotizaciones=[_cot()], enviar=True
    )
    assert res.estado == EstadoSolicitudGestion.COTIZACION
    assert res.proyectista_id == 55
    assert repo.count_archivos_categoria(1, "cotizacion") == 1


def test_proyectos_no_puede_enviar_sin_cotizacion():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.COTIZACION_PROYECTOS))
    proy = _user(Role.PROYECTOS, 55, "proy")
    with pytest.raises(ValueError, match="al menos una cotización"):
        EnviarCotizacionProyectos(repo, FakeStorage()).execute(
            proy, 1, cotizaciones=[], enviar=True
        )


def test_compras_envia_cotizacion_va_a_mesa_tecnica():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.COTIZACION))
    repo.s.gestor_id = 7
    compras = _user(Role.COMPRAS, 7, "compras")
    res = EnviarCotizacionSolicitud(repo, FakeStorage()).execute(
        compras,
        1,
        cotizaciones=[_cot()],
        justificacion="Única cotización viable",
    )
    assert res.estado == EstadoSolicitudGestion.COMITE
    assert res.comite_supervisor_ok is False
    assert res.comite_proyectos_ok is False


def test_comite_ambos_aceptan_pasa_a_segunda_aprobacion():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.COMITE))
    repo.s.proyectista_id = 55
    supervisor = _user(Role.SOLICITANTE, 10, "sup")
    proy = _user(Role.PROYECTOS, 55, "proy")
    uc = ResolverComiteTecnico(repo, FakeStorage())

    r1 = uc.aceptar(supervisor, 1)
    assert r1.estado == EstadoSolicitudGestion.COMITE
    assert r1.comite_supervisor_ok is True
    assert r1.comite_proyectos_ok is False

    r2 = uc.aceptar(proy, 1)
    assert r2.estado == EstadoSolicitudGestion.EN_APROBACION
    assert r2.comite_supervisor_ok and r2.comite_proyectos_ok


def test_diego_aprueba_tras_comite_pasa_a_gestionando():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.EN_APROBACION))
    repo.add_archivos(
        1,
        [
            SolicitudGestionArchivo(
                nombre_original="c.pdf",
                ruta_almacenamiento="x",
                mime_type="application/pdf",
                tamano_bytes=1,
                categoria="cotizacion",
                valor_cotizacion=Decimal("7000000"),
                propuesta=True,
            )
        ],
    )
    admin = _user(Role.ADMIN, 1, "admin")
    res = ResolverAprobacionSolicitud(repo).aprobar(admin, 1, cotizacion_elegida_id=1)
    assert res.estado == EstadoSolicitudGestion.GESTIONANDO_SERVICIO


def test_comite_recotizar_vuelve_a_proyectos():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.COMITE))
    repo.s.comite_supervisor_ok = True
    supervisor = _user(Role.SOLICITANTE, 10, "sup")
    res = ResolverComiteTecnico(repo, FakeStorage()).recotizar(supervisor, 1)
    assert res.estado == EstadoSolicitudGestion.COTIZACION_PROYECTOS
    assert res.comite_supervisor_ok is False
    assert res.comite_proyectos_ok is False


def test_comite_extrano_no_puede_aceptar():
    repo = FakeRepo(_srv(EstadoSolicitudGestion.COMITE))
    ajeno = _user(Role.COMPRAS, 99, "compras")
    from app.domain.exceptions import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        ResolverComiteTecnico(repo, FakeStorage()).aceptar(ajeno, 1)
