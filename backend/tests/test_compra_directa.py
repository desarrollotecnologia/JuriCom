"""Compra directa a Compras: nace en Primera Aprobación (salta aprobación del líder)
con productos aprobados; Compras puede devolverla al flujo normal de aprobación.
"""

import json
from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    RegistrarSolicitudCompra,
)
from app.application.use_cases.solicitudes_gestion.enviar_compra_a_aprobacion import (
    EnviarCompraAAprobacion,
)
from app.domain.entities.user import User
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role


class FakeStorage:
    def save(self, *, contenido, nombre_original, mime_type, subcarpeta=""):
        return SimpleNamespace(
            nombre_original=nombre_original,
            ruta=f"{subcarpeta}/{nombre_original}",
            mime_type=mime_type,
            tamano_bytes=len(contenido or b""),
        )


class FakeRepo:
    def __init__(self):
        self.s = None
        self.estados_productos = None
        self.historial = []

    def create(self, solicitud):
        for i, p in enumerate(solicitud.productos, start=1):
            p.id = i
            p.solicitud_id = 1
        solicitud.id = 1
        solicitud.codigo = "C-0001"
        self.s = solicitud
        return solicitud

    def get_by_id(self, solicitud_id):
        return self.s

    def update(self, solicitud):
        self.s = solicitud
        return solicitud

    def registrar_historial(self, solicitud_id, estado, *, usuario_id, comentario):
        self.historial.append((estado, comentario))

    def update_productos_estado_aprobacion(self, solicitud_id, estados):
        self.estados_productos = dict(estados)
        for p in self.s.productos:
            if p.id in estados:
                p.estado_aprobacion = EstadoAprobacionProducto(estados[p.id])

    def count_archivos_categoria(self, solicitud_id, categoria):
        return 0

    def add_archivos(self, solicitud_id, archivos):
        return []


class FakeNotificador:
    def __init__(self):
        self.eventos = []

    def notificar_solicitud_creada(self, solicitud, actor):
        self.eventos.append("creada")

    def notificar_compra_directa_creada(self, solicitud, actor):
        self.eventos.append("directa_creada")

    def notificar_compra_enviada_a_aprobacion(self, solicitud, actor):
        self.eventos.append("enviada_aprobacion")


def _actor(role=Role.SOLICITANTE, id=10):
    return User(username="u", password_hash="x", role=role, id=id, email="u@colbeef.com")


def _productos_json():
    return json.dumps(
        [{"descripcion": "TORNILLOS", "unidad": "CAJA", "centro_costo": "212-7", "cantidad": "5"}]
    )


def _crear(repo, notif, directa):
    return RegistrarSolicitudCompra(repo, FakeStorage(), notif).execute(
        actor=_actor(),
        titulo="Compra marzo",
        presupuestado=True,
        centro_costo_area="212-7 TIC'S",
        lider_area_id="1056908061",
        lider_area_label="DIRECTORA",
        observaciones="",
        observaciones_texto="",
        productos_json=_productos_json(),
        archivos=[],
        directa_compras=directa,
    )


def test_directa_nace_en_primera_aprobacion_con_productos_aprobados():
    repo, notif = FakeRepo(), FakeNotificador()
    res = _crear(repo, notif, directa=True)

    assert res.directa_compras is True
    assert res.estado == EstadoSolicitudGestion.PRIMERA_APROBACION
    assert all(p.estado_aprobacion == EstadoAprobacionProducto.APROBADO for p in res.productos)
    assert notif.eventos == ["directa_creada"]


def test_normal_nace_en_solicitud_pendiente():
    repo, notif = FakeRepo(), FakeNotificador()
    res = _crear(repo, notif, directa=False)

    assert res.directa_compras is False
    assert res.estado == EstadoSolicitudGestion.SOLICITUD
    assert all(p.estado_aprobacion == EstadoAprobacionProducto.PENDIENTE for p in res.productos)
    assert notif.eventos == ["creada"]


def test_compras_envia_directa_a_aprobacion_del_lider():
    repo, notif = FakeRepo(), FakeNotificador()
    _crear(repo, notif, directa=True)

    compras = _actor(role=Role.COMPRAS, id=20)
    res = EnviarCompraAAprobacion(repo, notif).execute(compras, 1)

    # Vuelve al flujo normal: pendiente de aprobación del líder, sin gestor, ítems pendientes.
    assert res.estado == EstadoSolicitudGestion.SOLICITUD
    assert res.directa_compras is False
    assert res.gestor_id is None
    assert all(p.estado_aprobacion == EstadoAprobacionProducto.PENDIENTE for p in res.productos)
    assert "enviada_aprobacion" in notif.eventos


def test_no_se_puede_enviar_compra_normal_a_aprobacion():
    repo, notif = FakeRepo(), FakeNotificador()
    _crear(repo, notif, directa=False)

    compras = _actor(role=Role.COMPRAS, id=20)
    with pytest.raises(ValueError, match="compras directas"):
        EnviarCompraAAprobacion(repo, notif).execute(compras, 1)


def test_compra_directa_continua_a_tramite_oc_sin_segunda_aprobacion():
    from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
        EnviarCotizacionSolicitud,
    )

    repo, notif = FakeRepo(), FakeNotificador()
    _crear(repo, notif, directa=True)

    # Compras la tomó (Cotización) y es el gestor asignado.
    compras = _actor(role=Role.COMPRAS, id=20)
    repo.s.estado = EstadoSolicitudGestion.COTIZACION
    repo.s.gestor_id = compras.id

    res = EnviarCotizacionSolicitud(repo, FakeStorage(), notif).execute(
        compras,
        1,
        cotizaciones=[],
        directo_oc=True,
    )

    # Salta la 2.ª aprobación: pasa directo a Trámite OC, sin líder de segunda ni correo.
    assert res.estado == EstadoSolicitudGestion.TRAMITANDO_OC
    assert not res.lider_segunda_aprobacion_id
    assert notif.eventos == ["directa_creada"]
