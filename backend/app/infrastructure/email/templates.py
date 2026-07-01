"""Plantillas HTML y texto plano para los correos del sistema JURICOM_BEEF."""

from datetime import datetime
from html import escape
from typing import Iterable

from app.domain.entities.contrato import Contrato
from app.infrastructure.config import settings


_BRAND_COLOR = "#1f4e8a"
_BRAND_DARK = "#163966"
_GRAY = "#64748b"


_BASE_STYLES = f"""
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
    background-color: #f5f7fb;
    margin: 0;
    padding: 24px 0;
    color: #0f172a;
}}
.wrap {{ max-width: 640px; margin: 0 auto; padding: 0 16px; }}
.card {{
    background: #ffffff;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}}
.header {{
    background: {_BRAND_COLOR};
    padding: 24px 32px;
    color: white;
}}
.header h1 {{ font-size: 20px; margin: 0; font-weight: 600; letter-spacing: 0.5px; }}
.header p {{ font-size: 13px; margin: 4px 0 0; opacity: 0.85; }}
.content {{ padding: 32px; }}
h2 {{ color: {_BRAND_DARK}; font-size: 18px; margin: 0 0 16px; }}
.codigo {{
    display: inline-block;
    background: #e8f0fb;
    color: {_BRAND_DARK};
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-weight: 700;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 16px;
    letter-spacing: 1px;
}}
.row {{
    display: table;
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
}}
.row .label {{
    display: table-cell;
    color: {_GRAY};
    font-size: 13px;
    padding: 6px 12px 6px 0;
    width: 40%;
    vertical-align: top;
}}
.row .value {{
    display: table-cell;
    font-size: 14px;
    padding: 6px 0;
}}
.btn {{
    display: inline-block;
    background: {_BRAND_COLOR};
    color: white !important;
    text-decoration: none;
    padding: 12px 28px;
    border-radius: 8px;
    font-weight: 500;
    margin-top: 16px;
}}
.divider {{ height: 1px; background: #e2e8f0; margin: 24px 0; border: none; }}
.footer {{
    text-align: center;
    color: {_GRAY};
    font-size: 12px;
    margin-top: 24px;
    padding: 0 16px;
}}
.warn {{
    background: #fff7ed;
    border-left: 4px solid #d97706;
    padding: 12px 16px;
    border-radius: 6px;
    color: #92400e;
    font-size: 14px;
    margin: 16px 0;
}}
.table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
.table th, .table td {{
    text-align: left;
    padding: 8px 10px;
    font-size: 13px;
    border-bottom: 1px solid #e2e8f0;
}}
.table th {{ background: #f1f5f9; color: {_GRAY}; text-transform: uppercase; font-size: 11px; }}
"""


def _shell(titulo: str, contenido_html: str) -> str:
    """Envuelve el cuerpo del correo con el branding de JURICOM_BEEF."""
    año = datetime.now().year
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<title>{escape(titulo)}</title>
<style>{_BASE_STYLES}</style>
</head>
<body>
    <div class="wrap">
        <div class="card">
            <div class="header">
                <h1>JURICOM_BEEF</h1>
                <p>Sistema de gestión de contratos — Colbeef</p>
            </div>
            <div class="content">
                {contenido_html}
            </div>
        </div>
        <div class="footer">
            Este es un correo automático — no responder.<br>
            © {año} Colbeef · JURICOM_BEEF
        </div>
    </div>
</body>
</html>"""


def _moneda_label(c: Contrato) -> str:
    return f"{c.moneda.value} {c.valor:,.2f}"


def _plazo_label(c: Contrato) -> str:
    return f"{c.plazo_cantidad} {c.plazo_unidad.value}"


def _link_contrato(contrato_id: int) -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/app/compras/mis-solicitudes.html?contrato={contrato_id}"


def _link_aprobacion(contrato_id: int, paso: str, token: str) -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/api/v1/contratos/{contrato_id}/aprobar/{paso}?token={token}"


def _link_revision(contrato_id: int, paso: str, token: str) -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/api/v1/contratos/{contrato_id}/revision/{paso}?token={token}"


def _link_seguimiento(codigo: str, token: str) -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/app/seguimiento-contrato.html?codigo={codigo}&token={token}"


def _link_aprobar_otrosi(contrato_id: int, otrosi_id: int, paso: str, token: str) -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/api/v1/contratos/{contrato_id}/otrosi/{otrosi_id}/aprobar/{paso}?token={token}"


def _link_rechazar_otrosi(contrato_id: int, otrosi_id: int, paso: str, token: str) -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/api/v1/contratos/{contrato_id}/otrosi/{otrosi_id}/rechazar/{paso}?token={token}"


def _link_otrosies_pendientes() -> str:
    base = settings.public_url.rstrip("/")
    return f"{base}/app/juridica/otrosies-pendientes.html"


def _contrato_resumen_html(contrato: Contrato) -> str:
    return f"""
        <p style="margin: 20px 0;">
            Código: <span class="codigo">{escape(contrato.codigo or '')}</span>
        </p>
        <div class="row"><div class="label">Compañía</div><div class="value">{escape(contrato.compania)}</div></div>
        <div class="row"><div class="label">Proveedor</div><div class="value">{escape(contrato.proveedor_contratista)}</div></div>
        <div class="row"><div class="label">NIT</div><div class="value">{escape(contrato.nit_proveedor)}</div></div>
        <div class="row"><div class="label">Valor</div><div class="value">{_moneda_label(contrato)}</div></div>
        <div class="row"><div class="label">Plazo</div><div class="value">{_plazo_label(contrato)}</div></div>
        <div class="row"><div class="label">Renovación automática</div><div class="value">{'Sí' if contrato.renovacion_automatica else 'No'}</div></div>
        <div class="row"><div class="label">Requiere póliza</div><div class="value">{'Sí' if contrato.requiere_poliza else 'No'}</div></div>
        <hr class="divider" />
        <p><strong>Descripción del servicio</strong></p>
        <p>{escape(contrato.descripcion_servicio)}</p>
        <p><strong>Obligaciones Colbeef</strong></p>
        <p>{escape(contrato.obligaciones_colbeef)}</p>
        <p><strong>Obligaciones proveedor</strong></p>
        <p>{escape(contrato.obligaciones_proveedor)}</p>
        <p><strong>Condiciones de recibido satisfactorio</strong></p>
        <p>{escape(contrato.condiciones_recibido_satisfactorio)}</p>
    """


def _contrato_resumen_texto(contrato: Contrato) -> str:
    return (
        f"Código: {contrato.codigo}\n"
        f"Compañía: {contrato.compania}\n"
        f"Proveedor: {contrato.proveedor_contratista}\n"
        f"NIT: {contrato.nit_proveedor}\n"
        f"Valor: {_moneda_label(contrato)}\n"
        f"Plazo: {_plazo_label(contrato)}\n"
        f"Renovación automática: {'Sí' if contrato.renovacion_automatica else 'No'}\n"
        f"Requiere póliza: {'Sí' if contrato.requiere_poliza else 'No'}\n\n"
        f"Descripción:\n{contrato.descripcion_servicio}\n\n"
        f"Obligaciones Colbeef:\n{contrato.obligaciones_colbeef}\n\n"
        f"Obligaciones proveedor:\n{contrato.obligaciones_proveedor}\n\n"
        f"Condiciones recibido satisfactorio:\n"
        f"{contrato.condiciones_recibido_satisfactorio}\n"
    )


def render_aprobacion_lider_html(
    contrato: Contrato, radicado_por: str, token: str
) -> str:
    link = _link_revision(contrato.id, "lider", token)
    cuerpo = f"""
        <h2>Aprobación requerida del líder de proceso</h2>
        <p>
            El usuario <strong>{escape(radicado_por)}</strong> radicó una solicitud.
            Revisa toda la información detallada y decide si la apruebas o la rechazas.
        </p>
        {_contrato_resumen_html(contrato)}
        <p><a class="btn" href="{escape(link)}">Revisar solicitud</a></p>
    """
    return _shell("Aprobación líder de proceso", cuerpo)


def render_aprobacion_lider_texto(
    contrato: Contrato, radicado_por: str, token: str
) -> str:
    link = _link_revision(contrato.id, "lider", token)
    return (
        "JURICOM_BEEF — Aprobación líder de proceso\n\n"
        f"Radicado por: {radicado_por}\n\n"
        f"{_contrato_resumen_texto(contrato)}\n\n"
        f"Revisar solicitud: {link}\n"
    )


def render_aprobacion_gerencia_html(contrato: Contrato, token: str) -> str:
    link = _link_revision(contrato.id, "gerencia", token)
    cuerpo = f"""
        <h2>Aprobación requerida de Gerencia</h2>
        <p>
            El líder de proceso ya aprobó la solicitud. Revisa la información y,
            si está correcta, apruébala para que Jurídica pueda verla en Contratos.
            Si no cumple, puedes rechazarla.
        </p>
        {_contrato_resumen_html(contrato)}
        <p><a class="btn" href="{escape(link)}">Revisar solicitud</a></p>
    """
    return _shell("Aprobación Gerencia", cuerpo)


def render_aprobacion_gerencia_texto(contrato: Contrato, token: str) -> str:
    link = _link_revision(contrato.id, "gerencia", token)
    return (
        "JURICOM_BEEF — Aprobación Gerencia\n\n"
        f"{_contrato_resumen_texto(contrato)}\n\n"
        f"Revisar solicitud: {link}\n"
    )


def render_aprobado_juridica_html(contrato: Contrato) -> str:
    link = _link_contrato(contrato.id)
    cuerpo = f"""
        <h2>Contrato aprobado y pendiente por revisar</h2>
        <p>
            Líder de proceso y Gerencia aprobaron el contrato. Ya aparece en el
            módulo de Contratos para que Jurídica lo revise.
        </p>
        {_contrato_resumen_html(contrato)}
        <div class="warn">Estado del contrato: Pendiente / En proceso.</div>
        <p><a class="btn" href="{escape(link)}">Abrir contrato</a></p>
    """
    return _shell("Contrato aprobado para Jurídica", cuerpo)


def render_aprobado_juridica_texto(contrato: Contrato) -> str:
    return (
        "JURICOM_BEEF — Contrato aprobado y pendiente por revisar\n\n"
        f"{_contrato_resumen_texto(contrato)}\n\n"
        f"Abrir contrato: {_link_contrato(contrato.id)}\n"
    )


def render_seguimiento_lider_juridica_html(contrato: Contrato, token: str) -> str:
    seguimiento = _link_seguimiento(contrato.codigo or "", token)
    cuerpo = f"""
        <h2>Contrato enviado a Jurídica</h2>
        <p>
            Gerencia aprobó el contrato y ya fue enviado a Jurídica para su trámite.
            Puedes consultar el avance usando el código del contrato.
        </p>
        <p style="margin: 20px 0;">
            Código: <span class="codigo">{escape(contrato.codigo or '')}</span>
        </p>
        <div class="row"><div class="label">Proveedor</div><div class="value">{escape(contrato.proveedor_contratista)}</div></div>
        <div class="row"><div class="label">Estado actual</div><div class="value">En revisión jurídica</div></div>
        <p><a class="btn" href="{escape(seguimiento)}">Consultar seguimiento</a></p>
    """
    return _shell("Contrato enviado a Jurídica", cuerpo)


def render_seguimiento_lider_juridica_texto(contrato: Contrato, token: str) -> str:
    seguimiento = _link_seguimiento(contrato.codigo or "", token)
    return (
        "JURICOM_BEEF — Contrato enviado a Jurídica\n\n"
        "Gerencia aprobó el contrato y ya fue enviado a Jurídica para su trámite.\n\n"
        f"Código: {contrato.codigo}\n"
        f"Proveedor: {contrato.proveedor_contratista}\n"
        f"Seguimiento: {seguimiento}\n"
    )


def render_solicitud_otrosi_html(
    contrato: Contrato, otrosi, solicitado_por: str, token: str
) -> str:
    aprobar = _link_aprobar_otrosi(contrato.id, otrosi.id, "lider", token)
    rechazar = _link_rechazar_otrosi(contrato.id, otrosi.id, "lider", token)
    cuerpo = f"""
        <h2>Solicitud de otrosí registrada</h2>
        <p>
            El usuario <strong>{escape(solicitado_por)}</strong> registró una solicitud
            de otrosí para revisión del líder de proceso y Gerencia.
        </p>
        <p style="margin: 20px 0;">
            Contrato: <span class="codigo">{escape(contrato.codigo or '')}</span>
        </p>
        <hr class="divider" />
        <div class="row">
            <div class="label">Proveedor</div>
            <div class="value">{escape(contrato.proveedor_contratista)}</div>
        </div>
        <div class="row">
            <div class="label">Tipo de otrosí</div>
            <div class="value">{escape(otrosi.tipo.value)}</div>
        </div>
        <div class="row">
            <div class="label">Descripción / motivo</div>
            <div class="value">{escape(otrosi.descripcion)}</div>
        </div>
        <div class="row">
            <div class="label">Plazo adicional</div>
            <div class="value">
                {escape(str(otrosi.plazo_adicional_cantidad or '—'))}
                {escape(otrosi.plazo_adicional_unidad.value if otrosi.plazo_adicional_unidad else '')}
            </div>
        </div>
        <div class="row">
            <div class="label">Valor adicional</div>
            <div class="value">{escape(str(otrosi.valor_adicional or '—'))}</div>
        </div>
        <div class="warn">
            Nota: el PDF del otrosí firmado sólo debe ser cargado por Jurídica.
        </div>
        <p>
            <a class="btn" href="{escape(aprobar)}">Aprobar otrosí</a>
            <a class="btn" href="{escape(rechazar)}" style="background:#991b1b;">Rechazar otrosí</a>
        </p>
    """
    return _shell("Solicitud de otrosí registrada", cuerpo)


def render_solicitud_otrosi_texto(
    contrato: Contrato, otrosi, solicitado_por: str, token: str
) -> str:
    return (
        "JURICOM_BEEF — Solicitud de otrosí registrada\n\n"
        f"Contrato: {contrato.codigo}\n"
        f"Proveedor: {contrato.proveedor_contratista}\n"
        f"Solicitado por: {solicitado_por}\n"
        f"Tipo: {otrosi.tipo.value}\n"
        f"Descripción: {otrosi.descripcion}\n"
        f"Plazo adicional: {otrosi.plazo_adicional_cantidad or '—'} "
        f"{otrosi.plazo_adicional_unidad.value if otrosi.plazo_adicional_unidad else ''}\n"
        f"Valor adicional: {otrosi.valor_adicional or '—'}\n\n"
        "Nota: el PDF del otrosí firmado sólo debe ser cargado por Jurídica.\n"
        f"Aprobar: {_link_aprobar_otrosi(contrato.id, otrosi.id, 'lider', token)}\n"
        f"Rechazar: {_link_rechazar_otrosi(contrato.id, otrosi.id, 'lider', token)}\n"
    )


def render_aprobacion_gerencia_otrosi_html(contrato: Contrato, otrosi, token: str) -> str:
    aprobar = _link_aprobar_otrosi(contrato.id, otrosi.id, "gerencia", token)
    rechazar = _link_rechazar_otrosi(contrato.id, otrosi.id, "gerencia", token)
    cuerpo = f"""
        <h2>Aprobación de otrosí requerida por Gerencia</h2>
        <p>El líder de proceso aprobó esta solicitud de otrosí.</p>
        <p>Contrato: <span class="codigo">{escape(contrato.codigo or '')}</span></p>
        <div class="row"><div class="label">Proveedor</div><div class="value">{escape(contrato.proveedor_contratista)}</div></div>
        <div class="row"><div class="label">Tipo</div><div class="value">{escape(otrosi.tipo.value)}</div></div>
        <div class="row"><div class="label">Descripción</div><div class="value">{escape(otrosi.descripcion)}</div></div>
        <p>
            <a class="btn" href="{escape(aprobar)}">Aprobar otrosí</a>
            <a class="btn" href="{escape(rechazar)}" style="background:#991b1b;">Rechazar otrosí</a>
        </p>
    """
    return _shell("Aprobación Gerencia otrosí", cuerpo)


def render_aprobacion_gerencia_otrosi_texto(contrato: Contrato, otrosi, token: str) -> str:
    return (
        "JURICOM_BEEF — Aprobación Gerencia de otrosí\n\n"
        f"Contrato: {contrato.codigo}\n"
        f"Proveedor: {contrato.proveedor_contratista}\n"
        f"Tipo: {otrosi.tipo.value}\n"
        f"Descripción: {otrosi.descripcion}\n\n"
        f"Aprobar: {_link_aprobar_otrosi(contrato.id, otrosi.id, 'gerencia', token)}\n"
        f"Rechazar: {_link_rechazar_otrosi(contrato.id, otrosi.id, 'gerencia', token)}\n"
    )


def render_otrosi_pendiente_juridica_html(contrato: Contrato, otrosi) -> str:
    cuerpo = f"""
        <h2>Otrosí pendiente para Jurídica</h2>
        <p>Líder de proceso y Gerencia aprobaron esta solicitud de otrosí.</p>
        <p>Contrato: <span class="codigo">{escape(contrato.codigo or '')}</span></p>
        <div class="row"><div class="label">Proveedor</div><div class="value">{escape(contrato.proveedor_contratista)}</div></div>
        <div class="row"><div class="label">Tipo</div><div class="value">{escape(otrosi.tipo.value)}</div></div>
        <div class="row"><div class="label">Descripción</div><div class="value">{escape(otrosi.descripcion)}</div></div>
        <div class="warn">Jurídica puede editar el otrosí, cargar el PDF firmado y aplicar la actualización sin reenviar a líder ni Gerencia.</div>
        <p><a class="btn" href="{escape(_link_otrosies_pendientes())}">Ver otrosíes pendientes</a></p>
    """
    return _shell("Otrosí pendiente Jurídica", cuerpo)


def render_otrosi_pendiente_juridica_texto(contrato: Contrato, otrosi) -> str:
    return (
        "JURICOM_BEEF — Otrosí pendiente para Jurídica\n\n"
        f"Contrato: {contrato.codigo}\n"
        f"Proveedor: {contrato.proveedor_contratista}\n"
        f"Tipo: {otrosi.tipo.value}\n"
        f"Descripción: {otrosi.descripcion}\n\n"
        "Jurídica puede editarlo, cargar el PDF firmado y aplicar la actualización.\n"
        f"Abrir pendientes: {_link_otrosies_pendientes()}\n"
    )


# ============================================================
# Notificación 1: contrato recién radicado
# ============================================================

def render_radicacion_html(contrato: Contrato, radicado_por: str) -> str:
    link = _link_contrato(contrato.id)
    cuerpo = f"""
        <h2>Nuevo contrato radicado</h2>
        <p>
            El usuario <strong>{escape(radicado_por)}</strong> acaba de radicar
            una solicitud de contrato que requiere revisión del equipo de
            Jurídica.
        </p>
        <p style="margin: 20px 0;">
            Código del contrato: <span class="codigo">{escape(contrato.codigo or '')}</span>
        </p>
        <hr class="divider" />
        <div class="row">
            <div class="label">Compañía</div>
            <div class="value">{escape(contrato.compania)}</div>
        </div>
        <div class="row">
            <div class="label">Proveedor</div>
            <div class="value">{escape(contrato.proveedor_contratista)}</div>
        </div>
        <div class="row">
            <div class="label">NIT</div>
            <div class="value">{escape(contrato.nit_proveedor)}</div>
        </div>
        <div class="row">
            <div class="label">Valor</div>
            <div class="value">{_moneda_label(contrato)}</div>
        </div>
        <div class="row">
            <div class="label">Plazo</div>
            <div class="value">{_plazo_label(contrato)}</div>
        </div>
        <div class="row">
            <div class="label">Renovación automática</div>
            <div class="value">{'Sí' if contrato.renovacion_automatica else 'No'}</div>
        </div>
        <div class="row">
            <div class="label">Requiere póliza</div>
            <div class="value">{'Sí — pendiente de adjuntar' if contrato.requiere_poliza else 'No'}</div>
        </div>
        <hr class="divider" />
        {('<div class="warn">Este contrato requiere póliza. Por favor adjúntala desde el sistema.</div>'
          if contrato.requiere_poliza else '')}
        <p>
            <a class="btn" href="{escape(link)}">Abrir contrato en el sistema</a>
        </p>
    """
    return _shell("Nuevo contrato radicado", cuerpo)


def render_radicacion_texto(contrato: Contrato, radicado_por: str) -> str:
    link = _link_contrato(contrato.id)
    poliza = "SÍ — pendiente de adjuntar" if contrato.requiere_poliza else "No"
    return (
        f"JURICOM_BEEF — Nuevo contrato radicado\n"
        f"\n"
        f"Código: {contrato.codigo}\n"
        f"Radicado por: {radicado_por}\n"
        f"\n"
        f"Compañía: {contrato.compania}\n"
        f"Proveedor: {contrato.proveedor_contratista}\n"
        f"NIT: {contrato.nit_proveedor}\n"
        f"Valor: {_moneda_label(contrato)}\n"
        f"Plazo: {_plazo_label(contrato)}\n"
        f"Renovación automática: {'Sí' if contrato.renovacion_automatica else 'No'}\n"
        f"Requiere póliza: {poliza}\n"
        f"\n"
        f"Abrir en el sistema: {link}\n"
    )


# ============================================================
# Notificación 2: resumen de contratos en proceso
# ============================================================

def render_pendientes_html(contratos: Iterable[Contrato]) -> str:
    contratos = list(contratos)
    if not contratos:
        cuerpo = """
            <h2>Sin contratos pendientes</h2>
            <p>No hay contratos en proceso en este momento. ¡Buen trabajo!</p>
        """
        return _shell("Sin contratos pendientes", cuerpo)

    filas = ""
    for c in contratos:
        link = _link_contrato(c.id)
        falta_poliza = "Sí" if c.requiere_poliza_y_no_la_tiene() else "—"
        falta_borrador = "Sí" if not c.tiene_borrador() else "—"
        filas += f"""
            <tr>
                <td><a href="{escape(link)}" style="color: {_BRAND_COLOR};"><strong>{escape(c.codigo or '')}</strong></a></td>
                <td>{escape(c.proveedor_contratista)}</td>
                <td>{_moneda_label(c)}</td>
                <td>{falta_poliza}</td>
                <td>{falta_borrador}</td>
            </tr>
        """

    cuerpo = f"""
        <h2>⚠ Contratos pendientes por finalizar</h2>
        <p>
            Hay <strong>{len(contratos)}</strong> contrato(s) en estado
            <em>En proceso</em>. Por favor revisa cada uno y completa los
            documentos faltantes (póliza y/o borrador firmado).
        </p>
        <div class="warn">
            Ojo: estos contratos aún no se han terminado de tramitar.
        </div>
        <table class="table">
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Proveedor</th>
                    <th>Valor</th>
                    <th>Falta póliza</th>
                    <th>Falta borrador</th>
                </tr>
            </thead>
            <tbody>{filas}</tbody>
        </table>
        <p style="margin-top: 20px;">
            <a class="btn" href="{escape(settings.public_url.rstrip('/'))}/app/compras/mis-solicitudes.html">
                Ver todos los contratos
            </a>
        </p>
    """
    return _shell("Contratos pendientes — JURICOM_BEEF", cuerpo)


def render_pendientes_texto(contratos: Iterable[Contrato]) -> str:
    contratos = list(contratos)
    if not contratos:
        return "JURICOM_BEEF\n\nNo hay contratos pendientes en este momento.\n"
    lineas = [
        "JURICOM_BEEF — Contratos pendientes por finalizar",
        "",
        f"Hay {len(contratos)} contrato(s) en estado 'En proceso'.",
        "",
    ]
    for c in contratos:
        lineas.append(f"- {c.codigo} | {c.proveedor_contratista} | {_moneda_label(c)}")
        if c.requiere_poliza_y_no_la_tiene():
            lineas.append("    · Falta: PÓLIZA")
        if not c.tiene_borrador():
            lineas.append("    · Falta: BORRADOR FIRMADO")
        lineas.append(f"    · {_link_contrato(c.id)}")
    return "\n".join(lineas) + "\n"


def render_entrega_solicitud_html(
    solicitud,
    estado,
    gestor_username: str,
) -> str:
    oc_general = (getattr(solicitud, "numero_tramite_oc", "") or "").strip()
    url = f"{settings.public_url.rstrip('/')}/app/compras/mis-solicitudes-gestion.html"
    mensaje_estado = (
        "Los ítems de tu solicitud fueron entregados completamente."
        if estado.value == "entregado"
        else "Los ítems de tu solicitud fueron entregados parcialmente."
    )
    oc_bloque = (
        f'<div class="row"><span class="label">Trámite OC</span>'
        f'<span class="value">{escape(oc_general)}</span></div>'
        if oc_general
        else ""
    )
    cuerpo = f"""
        <h2>Tu solicitud fue entregada</h2>
        <p>Hola <strong>{escape(solicitud.creado_por_username or "solicitante")}</strong>,</p>
        <p>{escape(mensaje_estado)}</p>
        <div class="row">
            <span class="label">Consecutivo</span>
            <span class="value"><span class="codigo">{escape(solicitud.codigo or "")}</span></span>
        </div>
        <div class="row">
            <span class="label">Estado</span>
            <span class="value"><strong>{escape(estado.label)}</strong></span>
        </div>
        <div class="row">
            <span class="label">Título</span>
            <span class="value">{escape(solicitud.titulo or "")}</span>
        </div>
        {oc_bloque}
        <div class="row">
            <span class="label">Gestor</span>
            <span class="value">{escape(gestor_username or "Compras")}</span>
        </div>
        <p style="margin-top: 20px;">
            <a class="btn" href="{escape(url)}">Ver mis solicitudes</a>
        </p>
    """
    return _shell(f"Solicitud {solicitud.codigo} — {estado.label}", cuerpo)


def render_entrega_solicitud_texto(
    solicitud,
    estado,
    gestor_username: str,
) -> str:
    oc_general = (getattr(solicitud, "numero_tramite_oc", "") or "").strip()
    url = f"{settings.public_url.rstrip('/')}/app/compras/mis-solicitudes-gestion.html"
    mensaje_estado = (
        "Los ítems de tu solicitud fueron entregados completamente."
        if estado.value == "entregado"
        else "Los ítems de tu solicitud fueron entregados parcialmente."
    )
    lineas = [
        "JURICOM_BEEF — Entrega de solicitud",
        "",
        f"Hola {solicitud.creado_por_username or 'solicitante'},",
        "",
        mensaje_estado,
        "",
        f"Consecutivo: {solicitud.codigo}",
        f"Estado: {estado.label}",
        f"Título: {solicitud.titulo}",
    ]
    if oc_general:
        lineas.append(f"Trámite OC: {oc_general}")
    lineas.extend(
        [
        f"Gestor: {gestor_username or 'Compras'}",
        "",
        f"Consulta el detalle en: {url}",
    ]
    )
    return "\n".join(lineas) + "\n"


def render_entrega_parcial_solicitud_html(
    solicitud,
    gestor_username: str,
    lineas: list[str],
) -> str:
    url = f"{settings.public_url.rstrip('/')}/app/compras/gestion-mis-solicitudes.html"
    items_html = "".join(f"<li>{escape(linea)}</li>" for linea in lineas)
    cuerpo = f"""
        <h2>Entrega parcial registrada</h2>
        <p>Hola <strong>{escape(solicitud.creado_por_username or "solicitante")}</strong>,</p>
        <p>Compras registró una entrega parcial de tu solicitud. Aún puede haber ítems pendientes.</p>
        <div class="row">
            <span class="label">Consecutivo</span>
            <span class="value"><span class="codigo">{escape(solicitud.codigo or "")}</span></span>
        </div>
        <div class="row">
            <span class="label">Gestor</span>
            <span class="value">{escape(gestor_username or "Compras")}</span>
        </div>
        <p><strong>Detalle de esta entrega:</strong></p>
        <ul>{items_html}</ul>
        <p style="margin-top: 20px;">
            <a class="btn" href="{escape(url)}">Ver mis solicitudes</a>
        </p>
    """
    return _shell(f"Solicitud {solicitud.codigo} — Entrega parcial", cuerpo)


def render_entrega_parcial_solicitud_texto(
    solicitud,
    gestor_username: str,
    lineas: list[str],
) -> str:
    url = f"{settings.public_url.rstrip('/')}/app/compras/gestion-mis-solicitudes.html"
    lineas_txt = "\n".join(f"- {linea}" for linea in lineas)
    return (
        "JURICOM_BEEF — Entrega parcial registrada\n\n"
        f"Hola {solicitud.creado_por_username or 'solicitante'},\n\n"
        "Compras registró una entrega parcial de tu solicitud.\n\n"
        f"Consecutivo: {solicitud.codigo}\n"
        f"Gestor: {gestor_username or 'Compras'}\n\n"
        f"Detalle:\n{lineas_txt}\n\n"
        f"Consulta el detalle en: {url}\n"
    )


def render_recepcion_insumos_solicitud_html(
    solicitud,
    gestor_username: str,
    lineas: list[str],
) -> str:
    url = f"{settings.public_url.rstrip('/')}/app/compras/gestion-mis-solicitudes.html"
    items_html = "".join(f"<li>{escape(linea)}</li>" for linea in lineas)
    cuerpo = f"""
        <h2>Insumos disponibles para reclamar</h2>
        <p>Hola <strong>{escape(solicitud.creado_por_username or "solicitante")}</strong>,</p>
        <p>Compras recibió físicamente ítems de tu solicitud. Ya puedes pasar a reclamarlos.</p>
        <div class="row">
            <span class="label">Consecutivo</span>
            <span class="value"><span class="codigo">{escape(solicitud.codigo or "")}</span></span>
        </div>
        <div class="row">
            <span class="label">Gestor</span>
            <span class="value">{escape(gestor_username or "Compras")}</span>
        </div>
        <p><strong>Ítems recibidos en esta recepción:</strong></p>
        <ul>{items_html}</ul>
        <p style="margin-top: 20px;">
            <a class="btn" href="{escape(url)}">Ver mis solicitudes</a>
        </p>
    """
    return _shell(f"Solicitud {solicitud.codigo} — Recepción de insumos", cuerpo)


def render_recepcion_insumos_solicitud_texto(
    solicitud,
    gestor_username: str,
    lineas: list[str],
) -> str:
    url = f"{settings.public_url.rstrip('/')}/app/compras/gestion-mis-solicitudes.html"
    lineas_txt = "\n".join(f"- {linea}" for linea in lineas)
    return (
        "JURICOM_BEEF — Insumos disponibles para reclamar\n\n"
        f"Hola {solicitud.creado_por_username or 'solicitante'},\n\n"
        "Compras recibió físicamente ítems de tu solicitud. Ya puedes pasar a reclamarlos.\n\n"
        f"Consecutivo: {solicitud.codigo}\n"
        f"Gestor: {gestor_username or 'Compras'}\n\n"
        f"Ítems recibidos:\n{lineas_txt}\n\n"
        f"Consulta el detalle en: {url}\n"
    )
