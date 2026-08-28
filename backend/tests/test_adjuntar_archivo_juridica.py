"""Póliza: sólo Jurídica/Gerencia, durante elaboración."""

from types import SimpleNamespace

import pytest

from app.application.use_cases.contratos.adjuntar_archivo_juridica import (
    AdjuntarArchivoJuridica,
    ArchivoJuridicaEntrada,
)
from app.domain.entities.contrato import TipoArchivo
from app.domain.exceptions import UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato


class FakeRepo:
    def __init__(self, contrato):
        self._contrato = contrato
        self.added = None

    def get_by_id(self, _id):
        return self._contrato

    def add_archivo(self, archivo):
        self.added = archivo
        return archivo


class FakeStorage:
    def save(self, **kwargs):
        return SimpleNamespace(
            nombre_original=kwargs["nombre_original"],
            ruta="contratos/poliza.pdf",
            mime_type=kwargs["mime_type"],
            tamano_bytes=len(kwargs["contenido"]),
        )


def _actor(rol):
    return SimpleNamespace(
        id=1,
        is_admin=lambda: rol == "admin",
        is_juridica=lambda: rol == "juridica",
        is_compras=lambda: rol == "compras",
    )


def _contrato(estado=EstadoContrato.ELABORANDO):
    return SimpleNamespace(
        id=10,
        estado=estado,
        estado_aprobacion=EstadoAprobacion.APROBADO,
    )


def _entrada():
    return ArchivoJuridicaEntrada(
        tipo=TipoArchivo.POLIZA,
        nombre_original="poliza.pdf",
        mime_type="application/pdf",
        contenido=b"%PDF-1.4",
    )


def test_compras_no_puede_subir_poliza():
    uc = AdjuntarArchivoJuridica(FakeRepo(_contrato()), FakeStorage())
    with pytest.raises(UnauthorizedError):
        uc.execute(_actor("compras"), 10, _entrada())


def test_juridica_sube_poliza_en_elaborando():
    repo = FakeRepo(_contrato(EstadoContrato.ELABORANDO))
    uc = AdjuntarArchivoJuridica(repo, FakeStorage())
    archivo = uc.execute(_actor("juridica"), 10, _entrada())
    assert archivo.tipo == TipoArchivo.POLIZA


def test_admin_sube_poliza_en_elaborando():
    repo = FakeRepo(_contrato(EstadoContrato.ELABORANDO))
    uc = AdjuntarArchivoJuridica(repo, FakeStorage())
    archivo = uc.execute(_actor("admin"), 10, _entrada())
    assert archivo.tipo == TipoArchivo.POLIZA


def test_poliza_no_se_sube_si_esta_finalizado():
    uc = AdjuntarArchivoJuridica(FakeRepo(_contrato(EstadoContrato.FINALIZADO)), FakeStorage())
    with pytest.raises(UnauthorizedError):
        uc.execute(_actor("juridica"), 10, _entrada())
