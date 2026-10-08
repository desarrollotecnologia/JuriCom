"""Módulo "Solicitudes que ya revisaste": decisiones del aprobador a partir del historial."""

from datetime import datetime

from app.application.use_cases.solicitudes_gestion.get_solicitud_gestion import (
    GetSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.listar_aprobaciones_realizadas import (
    ListarAprobacionesRealizadas,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionHistorialEstado as H,
)
from app.domain.entities.user import User
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion as E
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion

CREADOR, LIDER, GERENCIA, COMPRAS = 99, 10, 20, 30


def _h(etapa, uid, minuto):
    return H(etapa=etapa, usuario_id=uid, usuario_username=f"u{uid}", created_at=datetime(2026, 10, 8, 8, minuto))


def _sg(sid, estado):
    return SolicitudGestion(
        id=sid, tipo=TipoSolicitudGestion.COMPRA, titulo="SG", creado_por_id=CREADOR,
        estado=estado, lider_area_id="otro-lider",
    )


SOLICITUDES = {1: _sg(1, E.ENTREGADO), 2: _sg(2, E.CANCELADO), 3: _sg(3, E.SOLICITUD)}
HISTORIAL = {
    # Compra completa: líder aprueba 1.ª, gerencia aprueba 2.ª, Compras sigue.
    1: [_h(E.SOLICITUD, CREADOR, 0), _h(E.PRIMERA_APROBACION, LIDER, 1), _h(E.EN_GESTION, COMPRAS, 2),
        _h(E.COTIZACION, COMPRAS, 3), _h(E.EN_APROBACION, COMPRAS, 4), _h(E.TRAMITANDO_OC, GERENCIA, 5),
        _h(E.ENTREGADO, COMPRAS, 6)],
    # El líder pide ajustes, el supervisor reenvía y el líder rechaza.
    2: [_h(E.SOLICITUD, CREADOR, 10), _h(E.REVISION, LIDER, 11), _h(E.SOLICITUD, CREADOR, 12),
        _h(E.CANCELADO, LIDER, 13)],
    # El supervisor solo editó: no hay decisión.
    3: [_h(E.SOLICITUD, CREADOR, 0), _h(E.SOLICITUD, CREADOR, 1)],
}


class FakeRepo:
    def historial_de_participante(self, uid):
        return {sid: h for sid, h in HISTORIAL.items() if uid is None or any(x.usuario_id == uid for x in h)}

    def list_all(self):
        return list(SOLICITUDES.values())

    def get_by_id(self, sid):
        return SOLICITUDES.get(sid)

    def get_historial(self, sid):
        return HISTORIAL.get(sid, [])


def _user(uid, role):
    return User(username=f"u{uid}", password_hash="x", role=role, id=uid, lider_catalog_id=f"cat{uid}")


def test_lider_ve_solo_sus_decisiones_mas_recientes_primero():
    items = ListarAprobacionesRealizadas(FakeRepo()).execute(_user(LIDER, Role.LIDER_APROBADOR))
    assert [(a.solicitud.id, a.decision) for a in items] == [
        (2, "Rechazó"), (2, "Pidió ajustes"), (1, "Aprobó (1.ª)"),
    ]


def test_segunda_aprobacion_y_admin_ve_todas():
    gerencia = ListarAprobacionesRealizadas(FakeRepo()).execute(_user(GERENCIA, Role.LIDER_APROBADOR))
    assert [(a.decision, a.etapa) for a in gerencia] == [("Aprobó (2.ª)", E.EN_APROBACION)]
    admin = ListarAprobacionesRealizadas(FakeRepo()).execute(_user(1, Role.ADMIN))
    assert len(admin) == 4  # las ediciones del creador no cuentan


def test_lider_puede_abrir_el_detalle_de_lo_que_reviso():
    caso = GetSolicitudGestion(FakeRepo())
    assert caso.execute(_user(LIDER, Role.LIDER_APROBADOR), 1).id == 1
    try:
        caso.execute(_user(GERENCIA, Role.LIDER_APROBADOR), 2)
    except Exception as e:
        assert "permiso" in str(e)
    else:
        raise AssertionError("Gerencia no participó en la 2 y no debería verla")
