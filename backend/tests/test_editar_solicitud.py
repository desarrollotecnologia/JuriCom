"""Editar una solicitud antes de la primera aprobación (corrección del solicitante).

- Solo el creador puede editar.
- Solo mientras está en estado "Solicitud" (antes de la primera aprobación).
- El cambio queda registrado en la trazabilidad (historial) con el detalle.
"""

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.editar_solicitud_gestion import (
    EditarSolicitudGestion,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion, SolicitudGestionProducto
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class FakeRepo:
    def __init__(self, solicitud):
        self.s = solicitud
        self.historial = []
        self.productos_reemplazados = None

    def get_by_id(self, solicitud_id):
        return self.s

    def update(self, solicitud):
        self.s = solicitud
        return solicitud

    def reemplazar_productos(self, solicitud_id, productos):
        self.productos_reemplazados = productos
        self.s.productos = productos

    def registrar_historial(self, solicitud_id, etapa, *, usuario_id=None, comentario=""):
        self.historial.append(SimpleNamespace(etapa=etapa, comentario=comentario))


def _actor(id=10):
    return User(username="pepe", password_hash="x", role=Role.SOLICITANTE, id=id)


def _solicitud(estado=EstadoSolicitudGestion.SOLICITUD, creador_id=10):
    return SolicitudGestion(
        tipo=TipoSolicitudGestion.COMPRA,
        titulo="Compra vieja",
        creado_por_id=creador_id,
        centro_costo_area="212-7",
        estado=estado,
        productos=[
            SolicitudGestionProducto(
                codigo_siimed="", unidad="UND", descripcion="valvula inox",
                centro_costo="212-7", cantidad=Decimal("4"),
                estado_aprobacion=EstadoAprobacionProducto.PENDIENTE,
            )
        ],
    )


def _productos_json():
    return json.dumps([
        {"descripcion": "valvula pvc", "unidad": "UND", "centro_costo": "212-7", "cantidad": "6"},
        {"descripcion": "tuerca", "unidad": "UND", "centro_costo": "212-7", "cantidad": "2"},
    ])


def test_editar_antes_de_aprobacion_actualiza_y_registra_traza():
    repo = FakeRepo(_solicitud())
    res = EditarSolicitudGestion(repo).execute(
        _actor(),
        1,
        titulo="Compra corregida",
        productos_json=_productos_json(),
    )

    assert res.titulo == "Compra corregida"
    assert repo.productos_reemplazados is not None
    assert [p.descripcion for p in res.productos] == ["valvula pvc", "tuerca"]
    # Quedó registrado en la trazabilidad con el detalle del cambio.
    assert len(repo.historial) == 1
    comentario = repo.historial[0].comentario
    assert "editada por pepe" in comentario.lower()
    assert "Compra corregida" in comentario  # título nuevo en el detalle
    assert "valvula pvc" in comentario  # ítem agregado


def test_no_creador_no_puede_editar():
    repo = FakeRepo(_solicitud(creador_id=10))
    with pytest.raises(UnauthorizedError):
        EditarSolicitudGestion(repo).execute(_actor(id=99), 1, titulo="Hack")


def test_no_se_puede_editar_despues_de_primera_aprobacion():
    repo = FakeRepo(_solicitud(estado=EstadoSolicitudGestion.PRIMERA_APROBACION))
    with pytest.raises(ValueError, match="antes de la primera aprobación"):
        EditarSolicitudGestion(repo).execute(_actor(), 1, titulo="Tarde")


def test_editar_sin_cambios_falla():
    repo = FakeRepo(_solicitud())
    with pytest.raises(ValueError, match="No hay cambios"):
        EditarSolicitudGestion(repo).execute(_actor(), 1, titulo="Compra vieja")
