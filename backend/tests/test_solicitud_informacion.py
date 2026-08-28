"""Reglas de la solicitud de información faltante (Jurídica <-> Supervisor)."""

from datetime import date
from types import SimpleNamespace

import pytest

from app.application.interfaces.file_storage import StoredFile
from app.application.use_cases.contratos.responder_informacion import (
    ArchivoRespuesta,
    ResponderInformacion,
)
from app.application.use_cases.contratos.solicitar_informacion import (
    ArchivoSolicitudInfo,
    SolicitarInformacion,
)
from app.domain.entities.contrato import TipoArchivo
from app.domain.entities.solicitud_informacion import (
    ESTADO_RESPONDIDA,
    SolicitudInformacion,
    calcular_fecha_limite_respuesta,
)
from app.domain.exceptions import UnauthorizedError


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


class FakeRepo:
    def __init__(self, contrato, solicitud=None):
        self._contrato = contrato
        self._solicitud = solicitud
        self.archivos = []
        self.creadas = []

    def get_by_id(self, contrato_id):
        return self._contrato

    def crear_solicitud_informacion(self, solicitud):
        solicitud.id = 1
        self.creadas.append(solicitud)
        self._solicitud = solicitud
        return solicitud

    def get_solicitud_informacion(self, solicitud_id):
        return self._solicitud

    def actualizar_solicitud_informacion(self, solicitud):
        self._solicitud = solicitud
        return solicitud

    def add_archivo(self, archivo):
        self.archivos.append(archivo)
        if self._solicitud is not None:
            self._solicitud.archivos.append(archivo)
        return archivo


def _actor(rol, actor_id=1):
    return SimpleNamespace(
        id=actor_id,
        is_admin=lambda: rol == "admin",
        is_compras=lambda: rol == "compras",
        is_juridica=lambda: rol == "juridica",
        is_solicitante=lambda: rol == "solicitante",
    )


def _contrato(supervisor_id=5, creado_por_id=7):
    return SimpleNamespace(
        id=10, creado_por_id=creado_por_id, supervisor_id=supervisor_id,
        codigo="JC-C-0001", proveedor_contratista="ACME",
    )


def _solicitud(estado="pendiente"):
    return SolicitudInformacion(
        id=1, contrato_id=10, solicitado_por_id=2, mensaje="Falta el RUT", estado=estado
    )


def test_juridica_puede_solicitar():
    repo = FakeRepo(_contrato())
    s = SolicitarInformacion(repo).execute(_actor("juridica", 2), 10, "Falta el RUT")
    assert s.estado == "pendiente"
    assert s.fecha_limite_respuesta is not None
    assert s.mensaje == "Falta el RUT"


def test_compras_no_puede_solicitar():
    repo = FakeRepo(_contrato())
    with pytest.raises(UnauthorizedError):
        SolicitarInformacion(repo).execute(_actor("compras", 5), 10, "algo")


def test_mensaje_vacio_falla():
    repo = FakeRepo(_contrato())
    with pytest.raises(ValueError):
        SolicitarInformacion(repo).execute(_actor("juridica", 2), 10, "   ")


def test_juridica_puede_adjuntar_fotos():
    repo = FakeRepo(_contrato())
    s = SolicitarInformacion(repo, FakeStorage()).execute(
        actor=_actor("juridica", 2),
        contrato_id=10,
        mensaje="Falta el RUT",
        archivos=[ArchivoSolicitudInfo("foto.jpg", "image/jpeg", b"xx")],
    )
    assert len(repo.archivos) == 1
    assert repo.archivos[0].tipo == TipoArchivo.SOLICITUD_INFORMACION
    assert repo.archivos[0].solicitud_informacion_id == 1
    assert len(s.archivos) == 1


def test_supervisor_puede_responder_con_archivos():
    repo = FakeRepo(_contrato(supervisor_id=5), _solicitud())
    s = ResponderInformacion(repo, FakeStorage()).execute(
        actor=_actor("solicitante", 5),
        contrato_id=10,
        solicitud_id=1,
        respuesta="Adjunto el RUT",
        archivos=[ArchivoRespuesta("rut.pdf", "application/pdf", b"x")],
    )
    assert s.estado == ESTADO_RESPONDIDA
    assert s.respondido_por_id == 5
    assert len(repo.archivos) == 1


def test_no_supervisor_no_puede_responder():
    repo = FakeRepo(_contrato(supervisor_id=99), _solicitud())
    with pytest.raises(UnauthorizedError):
        ResponderInformacion(repo, FakeStorage()).execute(
            actor=_actor("solicitante", 5), contrato_id=10, solicitud_id=1, respuesta="x"
        )


def test_compras_no_puede_responder():
    repo = FakeRepo(_contrato(supervisor_id=5), _solicitud())
    with pytest.raises(UnauthorizedError):
        ResponderInformacion(repo, FakeStorage()).execute(
            actor=_actor("compras", 5), contrato_id=10, solicitud_id=1, respuesta="x"
        )


def test_no_se_responde_dos_veces():
    repo = FakeRepo(_contrato(supervisor_id=5), _solicitud(estado="respondida"))
    with pytest.raises(ValueError):
        ResponderInformacion(repo, FakeStorage()).execute(
            actor=_actor("solicitante", 5), contrato_id=10, solicitud_id=1, respuesta="x"
        )


def test_fecha_limite_salta_fin_de_semana():
    viernes = date(2026, 7, 31)
    assert viernes.weekday() == 4
    limite = calcular_fecha_limite_respuesta(viernes, 2)
    assert limite == date(2026, 8, 4)


def test_dias_para_responder_countdown():
    hoy = date(2026, 7, 29)
    s = SolicitudInformacion(
        id=1, contrato_id=10, solicitado_por_id=2, mensaje="x",
        fecha_limite_respuesta=date(2026, 7, 31),
    )
    assert s.dias_para_responder(hoy) == 2
