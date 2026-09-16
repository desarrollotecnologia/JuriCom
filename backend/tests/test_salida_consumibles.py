"""Salida de consumibles: nace lista para entrega (sin aprobación) y notifica al líder.

Flujo esperado: crear -> RECEPCION_INSUMOS con productos aprobados y "recibidos",
notificando al solicitante, al líder (aviso) y a Compras.
"""

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.solicitudes_gestion.registrar_solicitud_salida_consumibles import (
    RegistrarSolicitudSalidaConsumibles,
)
from app.domain.entities.user import User
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.roles import Role
from app.domain.value_objects.tipo_solicitud_gestion import (
    TipoSolicitudGestion,
    es_entrega_directa,
)


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
        self.recibidas = None

    def create(self, solicitud):
        for i, p in enumerate(solicitud.productos, start=1):
            p.id = i
            p.solicitud_id = 1
        solicitud.id = 1
        solicitud.codigo = "SC-0001"
        self.s = solicitud
        return solicitud

    def get_by_id(self, solicitud_id):
        return self.s

    def update_productos_cantidad_recibida(self, solicitud_id, cantidades):
        self.recibidas = dict(cantidades)
        for p in self.s.productos:
            if p.id in cantidades:
                p.cantidad_recibida = cantidades[p.id]


class FakeNotificador:
    def __init__(self):
        self.llamado_con = None

    def notificar_salida_consumibles_creada(self, solicitud, actor):
        self.llamado_con = (solicitud, actor)


def _actor():
    return User(username="supervisor", password_hash="x", role=Role.SOLICITANTE, id=10, email="sup@colbeef.com")


def _productos_json():
    return json.dumps(
        [
            {"codigo_siimed": "1001", "descripcion": "GUANTES", "unidad": "CAJA", "cantidad": "3"},
            {"codigo_siimed": "1002", "descripcion": "TAPABOCAS", "unidad": "CAJA", "cantidad": 2},
        ]
    )


def _ejecutar(repo, notif):
    return RegistrarSolicitudSalidaConsumibles(repo, FakeStorage(), notif).execute(
        actor=_actor(),
        titulo="Consumibles marzo",
        centro_costo_area="212-7 TIC'S",
        area_consumo="",
        lider_area_id="1056908061",
        lider_area_label="DIRECTORA DE PLANTA",
        observaciones="",
        observaciones_texto="",
        productos_json=_productos_json(),
        archivos=[],
    )


def test_nace_lista_para_entrega_sin_aprobacion():
    repo, notif = FakeRepo(), FakeNotificador()
    res = _ejecutar(repo, notif)

    assert res.tipo == TipoSolicitudGestion.SALIDA_CONSUMIBLES
    assert res.estado == EstadoSolicitudGestion.RECEPCION_INSUMOS
    # Sin aprobación: los ítems quedan aprobados y "recibidos" = cantidad.
    assert all(p.estado_aprobacion == EstadoAprobacionProducto.APROBADO for p in res.productos)
    assert repo.recibidas == {1: Decimal("3"), 2: Decimal("2")}
    # El área del solicitante se aplica a cada ítem.
    assert all(p.area_consumo == "212-7 TIC'S" for p in res.productos)
    # Entrega directa: sin OC ni recepción física.
    assert es_entrega_directa(res.tipo) is True
    assert res.tiene_tramite_oc_registrado is True
    # Se notificó (solicitante + líder + compras) vía el método dedicado.
    assert notif.llamado_con is not None
    # Prioridad por defecto.
    assert res.prioridad == "media"


def test_prioridad_se_normaliza():
    repo, notif = FakeRepo(), FakeNotificador()
    res = RegistrarSolicitudSalidaConsumibles(repo, FakeStorage(), notif).execute(
        actor=_actor(),
        titulo="Consumibles urgentes",
        centro_costo_area="212-7 TIC'S",
        area_consumo="",
        lider_area_id="1056908061",
        lider_area_label="",
        observaciones="",
        observaciones_texto="",
        productos_json=_productos_json(),
        archivos=[],
        prioridad="ALTA ",
    )
    assert res.prioridad == "alta"

    res2 = RegistrarSolicitudSalidaConsumibles(FakeRepo(), FakeStorage(), FakeNotificador()).execute(
        actor=_actor(),
        titulo="Consumibles",
        centro_costo_area="212-7 TIC'S",
        area_consumo="",
        lider_area_id="1056908061",
        lider_area_label="",
        observaciones="",
        observaciones_texto="",
        productos_json=_productos_json(),
        archivos=[],
        prioridad="lo-que-sea",
    )
    assert res2.prioridad == "media"


def test_rechaza_sin_consumibles():
    repo, notif = FakeRepo(), FakeNotificador()
    with pytest.raises(ValueError, match="al menos un consumible"):
        RegistrarSolicitudSalidaConsumibles(repo, FakeStorage(), notif).execute(
            actor=_actor(),
            titulo="Vacía",
            centro_costo_area="212-7 TIC'S",
            area_consumo="",
            lider_area_id="1056908061",
            lider_area_label="",
            observaciones="",
            observaciones_texto="",
            productos_json="[]",
            archivos=[],
        )
