"""Eventos del contrato quedan en el historial de la SRV vinculada."""

from types import SimpleNamespace

from app.application.services.trazabilidad_contrato_srv import (
    etapa_historial_contrato,
    etiqueta_estado_contrato,
    registrar_evento_contrato_en_srv,
    registrar_observacion_contrato_en_srv,
)
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion


class FakeSolicitudes:
    def __init__(self, solicitud=None):
        self._solicitud = solicitud
        self.historial = []

    def get_by_id(self, solicitud_id):
        if self._solicitud and self._solicitud.id == solicitud_id:
            return self._solicitud
        return None

    def registrar_historial(self, solicitud_id, etapa, *, usuario_id=None, comentario=""):
        self.historial.append(
            {
                "solicitud_id": solicitud_id,
                "etapa": etapa,
                "usuario_id": usuario_id,
                "comentario": comentario,
            }
        )

    def update(self, solicitud):
        self.actualizada = solicitud
        return solicitud

    def add_observacion(self, solicitud_id, observacion):
        self.observaciones = getattr(self, "observaciones", [])
        self.observaciones.append(observacion)
        return observacion


def test_sin_srv_no_escribe():
    repo = FakeSolicitudes()
    registrar_evento_contrato_en_srv(
        repo, SimpleNamespace(solicitud_gestion_id=None, codigo="OS-0001"), 1, "hola"
    )
    assert repo.historial == []


def test_escribe_comentario_en_historial_srv():
    solicitud = SimpleNamespace(id=6, estado="gestionando_servicio")
    repo = FakeSolicitudes(solicitud)
    contrato = SimpleNamespace(solicitud_gestion_id=6, codigo="OS-0004")
    registrar_evento_contrato_en_srv(
        repo,
        contrato,
        3,
        "Jurídica solicitó información al supervisor (OS-0004): Falta el RUT",
        etapa=EstadoSolicitudGestion.SOLICITANDO_INFO,
    )
    assert len(repo.historial) == 1
    assert repo.historial[0]["solicitud_id"] == 6
    assert repo.historial[0]["usuario_id"] == 3
    assert repo.historial[0]["etapa"] == EstadoSolicitudGestion.SOLICITANDO_INFO
    assert "Falta el RUT" in repo.historial[0]["comentario"]


def test_nuevo_estado_actualiza_la_srv():
    solicitud = SimpleNamespace(id=6, estado="gestionando_servicio")
    repo = FakeSolicitudes(solicitud)
    contrato = SimpleNamespace(solicitud_gestion_id=6, codigo="OS-0004")
    registrar_evento_contrato_en_srv(
        repo,
        contrato,
        3,
        "Supervisor finalizó OS-0004",
        etapa=EstadoSolicitudGestion.CONTRATO_FINALIZADO,
        nuevo_estado=EstadoSolicitudGestion.CONTRATO_FINALIZADO,
    )
    assert solicitud.estado == EstadoSolicitudGestion.CONTRATO_FINALIZADO
    assert repo.actualizada is solicitud


def test_sin_nuevo_estado_no_toca_la_srv():
    solicitud = SimpleNamespace(id=6, estado="gestionando_servicio")
    repo = FakeSolicitudes(solicitud)
    registrar_evento_contrato_en_srv(
        repo, SimpleNamespace(solicitud_gestion_id=6, codigo="C-0001"), 1, "hola"
    )
    assert solicitud.estado == "gestionando_servicio"
    assert not hasattr(repo, "actualizada")


def test_trunca_comentarios_largos():
    solicitud = SimpleNamespace(id=6, estado="gestionando_servicio")
    repo = FakeSolicitudes(solicitud)
    registrar_evento_contrato_en_srv(
        repo, SimpleNamespace(solicitud_gestion_id=6, codigo="C-0001"), 1, "x" * 500
    )
    assert len(repo.historial[0]["comentario"]) == 400


def test_etiqueta_estado_contrato():
    assert etiqueta_estado_contrato(EstadoContrato.EN_PROCESO) == "Pendiente"
    assert etiqueta_estado_contrato(EstadoContrato.ELABORANDO) == "Elaborando contrato"
    assert etiqueta_estado_contrato("activo") == "Activo"


def test_etapa_historial_contrato():
    assert etapa_historial_contrato(EstadoContrato.EN_PROCESO) == EstadoSolicitudGestion.EN_JURIDICA
    assert (
        etapa_historial_contrato(EstadoContrato.ELABORANDO)
        == EstadoSolicitudGestion.ELABORANDO_CONTRATO
    )
    assert etapa_historial_contrato("activo") == EstadoSolicitudGestion.CONTRATO_ACTIVO


def test_nuevos_estados_contrato_tienen_label_y_etapa():
    assert etiqueta_estado_contrato(EstadoContrato.REVISION_POLIZAS) == "Revisión de pólizas"
    assert etiqueta_estado_contrato(EstadoContrato.SOLICITUD_FIRMAS) == "Solicitud de firmas"
    assert (
        etapa_historial_contrato(EstadoContrato.REVISION_POLIZAS)
        == EstadoSolicitudGestion.REVISION_POLIZAS
    )
    assert (
        etapa_historial_contrato(EstadoContrato.SOLICITUD_FIRMAS)
        == EstadoSolicitudGestion.SOLICITUD_FIRMAS
    )


def test_observacion_se_registra_en_historial_de_observaciones():
    solicitud = SimpleNamespace(id=6, estado="en_juridica")
    repo = FakeSolicitudes(solicitud)
    contrato = SimpleNamespace(solicitud_gestion_id=6, codigo="C-0004")
    actor = SimpleNamespace(id=3, username="abogado", role="juridica")
    registrar_observacion_contrato_en_srv(repo, contrato, actor, "  Falta firma del gerente  ")
    assert len(repo.observaciones) == 1
    obs = repo.observaciones[0]
    assert obs.contenido_texto == "Falta firma del gerente"
    assert "Falta firma del gerente" in obs.contenido
    assert obs.usuario_id == 3


def test_observacion_vacia_no_registra_nada():
    solicitud = SimpleNamespace(id=6, estado="en_juridica")
    repo = FakeSolicitudes(solicitud)
    contrato = SimpleNamespace(solicitud_gestion_id=6, codigo="C-0004")
    actor = SimpleNamespace(id=3, username="abogado", role="juridica")
    registrar_observacion_contrato_en_srv(repo, contrato, actor, "   ")
    assert not hasattr(repo, "observaciones")
