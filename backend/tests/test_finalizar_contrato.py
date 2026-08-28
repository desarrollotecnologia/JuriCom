"""Reglas de cierre de contrato: informe final (supervisor) y acta de liquidación.

- valor <= umbral (15MM): el supervisor finaliza con solo el informe final.
- valor  > umbral: el supervisor entrega el informe (queda ACTIVO) y Jurídica
  carga el acta de liquidación, que finaliza el contrato.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.interfaces.file_storage import StoredFile
from app.application.use_cases.contratos.finalizar_contrato import (
    ArchivoFinalizacion,
    CargarActaLiquidacion,
    FinalizarContratoCompras,
)
from app.domain.entities.contrato import TipoArchivo
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato

UMBRAL = Decimal("15000000")


class FakeStorage:
    def save(self, contenido, nombre_original, mime_type, subcarpeta):
        return StoredFile(
            ruta=f"contratos/{nombre_original}",
            nombre_original=nombre_original,
            mime_type=mime_type,
            tamano_bytes=len(contenido),
        )

    def delete(self, ruta):
        pass


class FakeContrato:
    def __init__(self, valor, supervisor_id=7):
        self.id = 10
        self.valor = Decimal(valor)
        self.supervisor_id = supervisor_id
        self.codigo = "C-0010"
        self.estado = EstadoContrato.ACTIVO
        self.estado_aprobacion = EstadoAprobacion.APROBADO
        self.archivos = []

    def tiene_informe_final(self):
        return any(a.tipo == TipoArchivo.INFORME_FINAL for a in self.archivos)

    def tiene_acta_liquidacion(self):
        return any(a.tipo == TipoArchivo.ACTA_LIQUIDACION for a in self.archivos)


class FakeRepo:
    def __init__(self, contrato):
        self._contrato = contrato
        self.archivos = []

    def get_by_id(self, contrato_id):
        return self._contrato

    def add_archivo(self, archivo):
        self.archivos.append(archivo)
        return archivo

    def update(self, contrato):
        return contrato


def _actor(rol="supervisor", actor_id=7):
    return SimpleNamespace(
        id=actor_id,
        is_admin=lambda: rol == "admin",
        is_compras=lambda: rol == "compras",
        is_juridica=lambda: rol == "juridica",
        is_solicitante=lambda: rol == "supervisor",
    )


def _archivo(tipo):
    return ArchivoFinalizacion(
        tipo=tipo, nombre_original="x.pdf", mime_type="application/pdf", contenido=b"x"
    )


def _fin(contrato):
    return FinalizarContratoCompras(FakeRepo(contrato), FakeStorage(), umbral_acta=UMBRAL)


def _acta(contrato):
    return CargarActaLiquidacion(FakeRepo(contrato), FakeStorage(), umbral_acta=UMBRAL)


# --- supervisor entrega informe final ---

def test_supervisor_no_asignado_no_puede_finalizar():
    with pytest.raises(UnauthorizedError):
        _fin(FakeContrato(5_000_000, supervisor_id=99)).execute(
            _actor("supervisor", actor_id=7), 10, _archivo(TipoArchivo.INFORME_FINAL)
        )


def test_juridica_no_puede_entregar_informe():
    with pytest.raises(UnauthorizedError):
        _fin(FakeContrato(5_000_000)).execute(
            _actor("juridica", actor_id=1), 10, _archivo(TipoArchivo.INFORME_FINAL)
        )


def test_sin_informe_falla():
    with pytest.raises(ValueError):
        _fin(FakeContrato(5_000_000)).execute(_actor(), 10, None)


def test_no_activo_falla():
    c = FakeContrato(5_000_000)
    c.estado = EstadoContrato.EN_PROCESO
    with pytest.raises(ValueError):
        _fin(c).execute(_actor(), 10, _archivo(TipoArchivo.INFORME_FINAL))


def test_menor_a_umbral_pasa_a_cierre_con_informe():
    # <= umbral: el informe final ya no finaliza directo; pasa al cierre contable.
    c = FakeContrato(5_000_000)
    result = _fin(c).execute(_actor(), 10, _archivo(TipoArchivo.INFORME_FINAL))
    assert result.estado == EstadoContrato.CIERRE_CONTABILIDAD
    assert c.tiene_informe_final()


def test_mayor_a_umbral_no_finaliza_queda_esperando_acta():
    c = FakeContrato(20_000_000)
    result = _fin(c).execute(_actor(), 10, _archivo(TipoArchivo.INFORME_FINAL))
    # No se finaliza: espera el acta de Jurídica.
    assert result.estado == EstadoContrato.ACTIVO
    assert c.tiene_informe_final()
    assert not c.tiene_acta_liquidacion()


# --- Jurídica carga el acta de liquidación (> umbral) ---

def test_solo_juridica_o_admin_carga_acta():
    c = FakeContrato(20_000_000)
    c.archivos.append(
        SimpleNamespace(tipo=TipoArchivo.INFORME_FINAL)
    )  # informe ya entregado
    with pytest.raises(UnauthorizedError):
        _acta(c).execute(_actor("supervisor"), 10, _archivo(TipoArchivo.ACTA_LIQUIDACION))


def test_acta_requiere_informe_previo():
    c = FakeContrato(20_000_000)  # sin informe final
    with pytest.raises(ValueError):
        _acta(c).execute(_actor("juridica", actor_id=1), 10, _archivo(TipoArchivo.ACTA_LIQUIDACION))


def test_acta_no_aplica_a_contratos_bajo_umbral():
    c = FakeContrato(5_000_000)
    c.archivos.append(SimpleNamespace(tipo=TipoArchivo.INFORME_FINAL))
    with pytest.raises(ValueError):
        _acta(c).execute(_actor("juridica", actor_id=1), 10, _archivo(TipoArchivo.ACTA_LIQUIDACION))


def test_flujo_mayor_a_umbral_completo():
    c = FakeContrato(20_000_000)
    # 1) Supervisor entrega informe → queda esperando acta.
    _fin(c).execute(_actor(), 10, _archivo(TipoArchivo.INFORME_FINAL))
    assert c.estado == EstadoContrato.ACTIVO
    # 2) Jurídica carga el acta → pasa al cierre contable (ya no finaliza directo).
    result = _acta(c).execute(
        _actor("juridica", actor_id=1), 10, _archivo(TipoArchivo.ACTA_LIQUIDACION)
    )
    assert result.estado == EstadoContrato.CIERRE_CONTABILIDAD
    assert c.tiene_acta_liquidacion()
