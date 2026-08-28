"""Flujo de cierre del contrato: informe/acta → Contabilidad → Tesorería → Completado.

Verifica que el supervisor ya no finalice directo (pasa a Cierre en contabilidad),
que Contabilidad envíe a Tesorería y que Tesorería complete el contrato, además de
los permisos por rol.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.use_cases.contratos.cierre_contrato import (
    ConfirmarCierreTesoreria,
    GestionarCierreContabilidad,
)
from app.application.use_cases.contratos.finalizar_contrato import (
    ArchivoFinalizacion,
    CargarActaLiquidacion,
    FinalizarContratoCompras,
)
from app.domain.entities.contrato import TipoArchivo
from app.domain.entities.user import User
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.roles import Role


class FakeRepo:
    def __init__(self, contrato):
        self._contrato = contrato

    def get_by_id(self, _id):
        return self._contrato

    def update(self, contrato):
        return contrato

    def add_archivo(self, archivo):
        return archivo


class FakeStorage:
    def save(self, *, contenido, nombre_original, mime_type, subcarpeta):
        return SimpleNamespace(
            nombre_original=nombre_original,
            ruta=f"{subcarpeta}/{nombre_original}",
            mime_type=mime_type,
            tamano_bytes=len(contenido),
        )


def _user(role: Role) -> User:
    return User(username=role.value, password_hash="x", role=role, id=1)


def _supervisor() -> User:
    return User(username="sup", password_hash="x", role=Role.SOLICITANTE, id=7)


def _contrato(**over):
    base = dict(
        id=10,
        estado=EstadoContrato.ACTIVO,
        estado_aprobacion=EstadoAprobacion.APROBADO,
        valor=Decimal("1000000"),
        supervisor_id=7,
        archivos=[],
        tiene_informe_final=lambda: True,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _archivo(tipo):
    return ArchivoFinalizacion(
        tipo=tipo, nombre_original="f.pdf", mime_type="application/pdf", contenido=b"x"
    )


def test_finalizar_menor_umbral_va_a_cierre_contabilidad():
    # Contrato <= 15M: el informe final ya no finaliza; pasa a Cierre en contabilidad.
    c = _contrato(valor=Decimal("1000000"))
    FinalizarContratoCompras(FakeRepo(c), FakeStorage()).execute(
        actor=_supervisor(), contrato_id=10, informe_final=_archivo(TipoArchivo.INFORME_FINAL)
    )
    assert c.estado == EstadoContrato.CIERRE_CONTABILIDAD


def test_acta_mayor_umbral_va_a_cierre_contabilidad():
    # Contrato > 15M: tras el acta de Jurídica pasa a Cierre en contabilidad (no finaliza).
    c = _contrato(valor=Decimal("20000000"))
    CargarActaLiquidacion(FakeRepo(c), FakeStorage()).execute(
        actor=_user(Role.JURIDICA),
        contrato_id=10,
        acta_liquidacion=_archivo(TipoArchivo.ACTA_LIQUIDACION),
    )
    assert c.estado == EstadoContrato.CIERRE_CONTABILIDAD


def test_flujo_cierre_contabilidad_tesoreria():
    c = _contrato(estado=EstadoContrato.CIERRE_CONTABILIDAD)
    repo = FakeRepo(c)

    GestionarCierreContabilidad(repo).execute(_user(Role.CONTABILIDAD), 10)
    assert c.estado == EstadoContrato.CIERRE_TESORERIA

    ConfirmarCierreTesoreria(repo).execute(_user(Role.TESORERIA), 10)
    assert c.estado == EstadoContrato.COMPLETADO


def test_permisos_cierre_por_rol():
    c = _contrato(estado=EstadoContrato.CIERRE_CONTABILIDAD)
    repo = FakeRepo(c)
    # Tesorería no puede gestionar la etapa de Contabilidad.
    with pytest.raises(UnauthorizedError):
        GestionarCierreContabilidad(repo).execute(_user(Role.TESORERIA), 10)
    # Contabilidad no puede confirmar el pago final.
    c.estado = EstadoContrato.CIERRE_TESORERIA
    with pytest.raises(UnauthorizedError):
        ConfirmarCierreTesoreria(repo).execute(_user(Role.CONTABILIDAD), 10)


def test_no_confirma_fuera_de_etapa():
    c = _contrato(estado=EstadoContrato.CIERRE_CONTABILIDAD)
    with pytest.raises(ValueError):
        ConfirmarCierreTesoreria(FakeRepo(c)).execute(_user(Role.TESORERIA), 10)


# --- Trazabilidad: las imágenes embebidas no deben desbordar la columna 'contenido' ---


class FakeSolicitudesRepo:
    def __init__(self):
        self.solicitud = SimpleNamespace(id=9)
        self.observaciones = {}
        self._next_arch_id = 100

    def get_by_id(self, _id):
        return self.solicitud

    def add_observacion(self, _sid, obs):
        obs.id = 1
        self.observaciones[1] = obs
        return obs

    def add_archivos(self, _sid, entidades, observacion_id=None):
        ids = []
        for _ in entidades:
            ids.append(self._next_arch_id)
            self._next_arch_id += 1
        return ids

    def update_observacion_contenido(self, obs_id, contenido):
        self.observaciones[obs_id].contenido = contenido

    def get_observacion_by_id(self, obs_id):
        return self.observaciones.get(obs_id)


def test_imagen_inline_se_extrae_y_no_queda_base64_en_contenido():
    from app.application.services.trazabilidad_contrato_srv import (
        registrar_observacion_contrato_en_srv,
    )

    # 1x1 PNG en base64, embebido como lo haría el editor.
    b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    html = f'<p>hola</p><img src="data:image/png;base64,{b64}" alt="x">'
    repo = FakeSolicitudesRepo()
    contrato = SimpleNamespace(solicitud_gestion_id=9, codigo="C-0001")

    registrar_observacion_contrato_en_srv(
        repo,
        contrato,
        _user(Role.TESORERIA),
        "hola",
        contexto="tesoreria",
        contenido_html=html,
        storage=FakeStorage(),
    )

    guardado = repo.observaciones[1].contenido
    assert "data:image/png;base64" not in guardado  # el base64 salió de la columna
    assert 'data-sg-archivo-id="100"' in guardado  # y quedó referenciando el archivo
