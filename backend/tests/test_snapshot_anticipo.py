"""El contrato copia (snapshot) el anticipo de la SRV al radicar."""

from decimal import Decimal
from types import SimpleNamespace

from app.application.use_cases.contratos.radicar_solicitud import (
    _cotizacion_elegida,
    _entrada_cotizacion_desde_srv,
    _snapshot_anticipo,
)
from app.domain.entities.contrato import TipoArchivo


def test_sin_srv_queda_sin_anticipo():
    snap = _snapshot_anticipo(None)
    assert snap == {
        "requiere_anticipo": False,
        "porcentaje_anticipo": None,
        "monto_anticipo": None,
        "observaciones_anticipo": "",
    }


def test_copia_anticipo_de_la_srv():
    srv = SimpleNamespace(
        requiere_anticipo=True,
        porcentaje_anticipo=Decimal("30"),
        monto_anticipo=Decimal("3000000"),
        observaciones_anticipo="Anticipo contra firma de acta.",
    )
    snap = _snapshot_anticipo(srv)
    assert snap["requiere_anticipo"] is True
    assert snap["porcentaje_anticipo"] == Decimal("30")
    assert snap["monto_anticipo"] == Decimal("3000000")
    assert snap["observaciones_anticipo"] == "Anticipo contra firma de acta."


def test_srv_sin_campos_no_rompe():
    srv = SimpleNamespace()
    snap = _snapshot_anticipo(srv)
    assert snap["requiere_anticipo"] is False
    assert snap["observaciones_anticipo"] == ""


def test_cotizacion_elegida_es_la_marcada_propuesta():
    srv = SimpleNamespace(
        archivos=[
            SimpleNamespace(categoria="cotizacion", propuesta=False, nombre_original="a.pdf"),
            SimpleNamespace(
                categoria="cotizacion",
                propuesta=True,
                nombre_original="elegida.pdf",
                ruta_almacenamiento="x",
                mime_type="application/pdf",
            ),
        ]
    )
    elegido = _cotizacion_elegida(srv)
    assert elegido.nombre_original == "elegida.pdf"


def test_copia_bytes_de_la_cotizacion_elegida():
    class FakeStorage:
        def read(self, ruta):
            assert ruta == "solicitudes/cotizaciones/x.pdf"
            return b"PDF-BYTES"

    srv = SimpleNamespace(
        archivos=[
            SimpleNamespace(
                categoria="cotizacion",
                propuesta=True,
                nombre_original="Minuta C-0002.docx",
                ruta_almacenamiento="solicitudes/cotizaciones/x.pdf",
                mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        ]
    )
    entrada = _entrada_cotizacion_desde_srv(srv, FakeStorage())
    assert entrada is not None
    assert entrada.tipo == TipoArchivo.COTIZACION
    assert entrada.nombre_original == "Minuta C-0002.docx"
    assert entrada.contenido == b"PDF-BYTES"
