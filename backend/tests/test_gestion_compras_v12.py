"""JURICOM 1.2: estado En gestión, anular solicitud y cambiar gestor (Compras)."""

from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.anular_solicitud_gestion import (
    AnularSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.cambiar_gestor_solicitud import (
    CambiarGestorSolicitud,
)
from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
    EnviarCotizacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.gestionar_solicitud_panel import (
    GestionarSolicitudPanel,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion as E
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class FakeRepo:
    def __init__(self, s):
        self.s = s
        self.historial = []
        self.observaciones = []

    def get_by_id(self, _):
        return self.s

    def update(self, s):
        self.s = s
        return s

    def registrar_historial(self, _sid, estado, *, usuario_id, comentario):
        self.historial.append((estado, comentario))

    def add_observacion(self, _sid, obs):
        obs.id = len(self.observaciones) + 1
        self.observaciones.append(obs)
        return obs

    def get_observacion_by_id(self, _):
        return None

    def count_archivos_categoria(self, *_):
        return 0


class FakeUsers:
    def __init__(self, *users):
        self.users = {u.id: u for u in users}

    def get_by_id(self, uid):
        return self.users.get(uid)

    def list_all(self):
        return list(self.users.values())


class FakeNotif:
    def __init__(self):
        self.eventos = []

    def notificar_anulacion(self, s, actor, motivo):
        self.eventos.append(("anulada", motivo))

    def notificar_cambio_gestor(self, s, actor, nuevo, comentario):
        self.eventos.append(("gestor", nuevo.username))


def _user(uid, role=Role.COMPRAS, activo=True):
    return User(username=f"u{uid}", password_hash="x", role=role, id=uid, email=f"u{uid}@colbeef.com", is_active=activo)


def _sg(estado, gestor_id=None, directa=False):
    return SolicitudGestion(
        id=1,
        tipo=TipoSolicitudGestion.COMPRA,
        titulo="SG",
        creado_por_id=99,
        estado=estado,
        gestor_id=gestor_id,
        directa_compras=directa,
        lider_area_id="1056908061",
    )


COMPRAS_A, COMPRAS_B, ADMIN = _user(1), _user(2), _user(3, Role.ADMIN)


# --- En gestión -------------------------------------------------------------

def test_gestionar_va_a_en_gestion_y_luego_a_cotizacion():
    repo = FakeRepo(_sg(E.PRIMERA_APROBACION))
    res = GestionarSolicitudPanel(repo).execute(COMPRAS_A, 1)
    assert res.estado == E.EN_GESTION and res.gestor_id == 1
    assert GestionarSolicitudPanel(repo).pasar_a_cotizacion(COMPRAS_A, 1).estado == E.COTIZACION


def test_pasar_a_cotizacion_exige_en_gestion():
    with pytest.raises(ValueError, match="En gestión"):
        GestionarSolicitudPanel(FakeRepo(_sg(E.PRIMERA_APROBACION))).pasar_a_cotizacion(COMPRAS_A, 1)


def test_menor_cuantia_va_directo_a_oc_desde_en_gestion():
    repo = FakeRepo(_sg(E.EN_GESTION, gestor_id=1, directa=True))
    res = EnviarCotizacionSolicitud(repo, SimpleNamespace()).execute(
        COMPRAS_A, 1, cotizaciones=[], directo_oc=True
    )
    assert res.estado == E.TRAMITANDO_OC


def test_compra_normal_no_cotiza_desde_en_gestion():
    repo = FakeRepo(_sg(E.EN_GESTION, gestor_id=1))
    with pytest.raises(ValueError, match="Cotización"):
        EnviarCotizacionSolicitud(repo, SimpleNamespace()).execute(
            COMPRAS_A, 1, cotizaciones=[], justificacion="x", lider_segunda_aprobacion_id="13542263"
        )


# --- Anular -----------------------------------------------------------------

def test_gestor_anula_en_cotizacion_con_motivo():
    repo, notif = FakeRepo(_sg(E.COTIZACION, gestor_id=1)), FakeNotif()
    res = AnularSolicitudGestion(repo, notif).execute(COMPRAS_A, 1, "Proveedor sin stock")
    assert res.estado == E.CANCELADO
    assert "Anulada por Compras" in repo.historial[-1][1]
    assert repo.observaciones and notif.eventos == [("anulada", "Proveedor sin stock")]


def test_anular_exige_motivo():
    with pytest.raises(ValueError, match="motivo"):
        AnularSolicitudGestion(FakeRepo(_sg(E.COTIZACION, gestor_id=1))).execute(COMPRAS_A, 1, "  ")


def test_otro_de_compras_no_anula():
    with pytest.raises(UnauthorizedError):
        AnularSolicitudGestion(FakeRepo(_sg(E.COTIZACION, gestor_id=1))).execute(COMPRAS_B, 1, "x")


def test_no_se_anula_con_oc_en_tramite():
    with pytest.raises(ValueError, match="orden de compra"):
        AnularSolicitudGestion(FakeRepo(_sg(E.TRAMITANDO_OC, gestor_id=1))).execute(ADMIN, 1, "x")


def test_admin_anula_en_primera_aprobacion():
    res = AnularSolicitudGestion(FakeRepo(_sg(E.PRIMERA_APROBACION))).execute(ADMIN, 1, "Duplicada")
    assert res.estado == E.CANCELADO


# --- Cambiar gestor ---------------------------------------------------------

def test_gestor_reasigna_a_otro_de_compras():
    repo, notif = FakeRepo(_sg(E.TRAMITANDO_OC, gestor_id=1)), FakeNotif()
    users = FakeUsers(COMPRAS_A, COMPRAS_B)
    res = CambiarGestorSolicitud(repo, users, notif).execute(COMPRAS_A, 1, 2, "Vacaciones")
    assert res.gestor_id == 2
    assert "a u2 por u1: Vacaciones" in repo.historial[-1][1]
    assert notif.eventos == [("gestor", "u2")]


def test_no_reasigna_a_quien_no_es_de_compras():
    users = FakeUsers(COMPRAS_A, _user(5, Role.SOLICITANTE))
    with pytest.raises(ValueError, match="Compras"):
        CambiarGestorSolicitud(FakeRepo(_sg(E.COTIZACION, gestor_id=1)), users).execute(COMPRAS_A, 1, 5)


def test_otro_de_compras_no_cambia_gestor_ajeno():
    users = FakeUsers(COMPRAS_A, COMPRAS_B)
    with pytest.raises(UnauthorizedError):
        CambiarGestorSolicitud(FakeRepo(_sg(E.COTIZACION, gestor_id=1)), users).execute(COMPRAS_B, 1, 2)


def test_lista_gestores_solo_compras_activos():
    users = FakeUsers(COMPRAS_A, _user(4, activo=False), _user(5, Role.SOLICITANTE))
    assert [u.id for u in CambiarGestorSolicitud(None, users).gestores_disponibles(COMPRAS_B)] == [1]
