"""Endpoints del módulo Solicitud Radicar (contratos)."""

import hashlib
import hmac
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, HTMLResponse

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.application.interfaces.file_storage import FileStorage
from app.application.use_cases.contratos import (
    AdjuntarArchivoJuridica,
    AplicarOtrosi,
    AprobarContrato,
    ArchivoEntrada,
    ArchivoJuridicaEntrada,
    ArchivoOtrosi,
    BuscarContratos,
    CambiarEstadoContrato,
    EditarContrato,
    GetContrato,
    RadicarSolicitud,
)
from app.application.use_cases.notifications import NotificarRadicacion
from app.domain.entities.contrato import ArchivoAdjunto, TipoArchivo
from app.domain.entities.user import User
from app.domain.exceptions import (
    ContratoNotFoundError,
    InvalidContratoStateError,
    InvalidFileError,
    MissingRequiredFileError,
    UnauthorizedError,
)
from app.domain.value_objects.estado_contrato import EstadoContrato
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_otrosi import TipoOtrosi
from app.domain.value_objects.unidad_plazo import UnidadPlazo
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
    get_email_notifier,
    get_file_storage,
)
from app.presentation.api.v1.schemas import (
    ArchivoResponse,
    CambiarEstadoRequest,
    ContratoListItem,
    ContratoResponse,
    EditarContratoRequest,
    OtrosiPendienteResponse,
    OtrosiResponse,
    SeguimientoContratoResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contratos", tags=["contratos"])


def _approval_token(contrato_id: int, paso: str) -> str:
    payload = f"{contrato_id}:{paso}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _validar_token(contrato_id: int, paso: str, token: str) -> bool:
    return hmac.compare_digest(_approval_token(contrato_id, paso), token or "")


def _validar_token_seguimiento(contrato_id: int, token: str) -> bool:
    return _validar_token(contrato_id, "lider", token)


def _otrosi_approval_token(contrato_id: int, otrosi_id: int, paso: str) -> str:
    payload = f"otrosi:{contrato_id}:{otrosi_id}:{paso}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _validar_otrosi_token(
    contrato_id: int, otrosi_id: int, paso: str, token: str
) -> bool:
    return hmac.compare_digest(
        _otrosi_approval_token(contrato_id, otrosi_id, paso), token or ""
    )


def _dias_para_vencer(c) -> Optional[int]:
    if not c.fecha_fin:
        return None
    return (c.fecha_fin - date.today()).days


def _umbral_vencimiento(c) -> int:
    if not c.fecha_inicio or not c.fecha_fin:
        return 30
    duracion = (c.fecha_fin - c.fecha_inicio).days
    return 7 if duracion <= 30 else 30


def _alerta_vencimiento(c) -> bool:
    dias = _dias_para_vencer(c)
    return c.estado.value == "activo" and dias is not None and 0 <= dias <= _umbral_vencimiento(c)


def _to_archivo_response(a) -> ArchivoResponse:
    return ArchivoResponse(
        id=a.id,
        tipo=a.tipo,
        nombre_original=a.nombre_original,
        mime_type=a.mime_type,
        tamano_bytes=a.tamano_bytes,
        subido_por_id=a.subido_por_id,
        created_at=a.created_at,
    )


def _to_otrosi_response(o) -> OtrosiResponse:
    return OtrosiResponse(
        id=o.id,
        numero=o.numero,
        tipo=o.tipo,
        descripcion=o.descripcion,
        plazo_adicional_cantidad=o.plazo_adicional_cantidad,
        plazo_adicional_unidad=o.plazo_adicional_unidad,
        valor_adicional=o.valor_adicional,
        nueva_descripcion_servicio=o.nueva_descripcion_servicio,
        archivo_id=o.archivo_id,
        estado_aprobacion=o.estado_aprobacion,
        aprobado_lider_at=o.aprobado_lider_at,
        aprobado_gerencia_at=o.aprobado_gerencia_at,
        creado_por_id=o.creado_por_id,
        created_at=o.created_at,
    )


def _to_contrato_response(c) -> ContratoResponse:
    return ContratoResponse(
        id=c.id,
        codigo=c.codigo,
        tipo_codigo=c.tipo_codigo,
        compania=c.compania,
        proveedor_contratista=c.proveedor_contratista,
        nit_proveedor=c.nit_proveedor,
        descripcion_servicio=c.descripcion_servicio,
        obligaciones_colbeef=c.obligaciones_colbeef,
        obligaciones_proveedor=c.obligaciones_proveedor,
        valor=c.valor,
        moneda=c.moneda,
        plazo_cantidad=c.plazo_cantidad,
        plazo_unidad=c.plazo_unidad,
        renovacion_automatica=c.renovacion_automatica,
        condiciones_recibido_satisfactorio=c.condiciones_recibido_satisfactorio,
        requiere_poliza=c.requiere_poliza,
        correo_lider_proceso=c.correo_lider_proceso,
        correo_gerencia=c.correo_gerencia,
        estado_aprobacion=c.estado_aprobacion,
        fecha_inicio=c.fecha_inicio,
        fecha_inicio_original=c.fecha_inicio_original,
        fecha_fin=c.fecha_fin,
        fecha_proxima_notificacion=c.fecha_proxima_notificacion,
        hora_proxima_notificacion=c.hora_proxima_notificacion,
        estado=c.estado,
        creado_por_id=c.creado_por_id,
        tiene_poliza=c.tiene_poliza(),
        tiene_borrador=c.tiene_borrador(),
        eliminado_at=c.eliminado_at,
        eliminado_por_id=c.eliminado_por_id,
        eliminado_observacion=c.eliminado_observacion,
        created_at=c.created_at,
        updated_at=c.updated_at,
        archivos=[_to_archivo_response(a) for a in c.archivos],
        otrosies=[_to_otrosi_response(o) for o in c.otrosies],
    )


def _to_list_item(c) -> ContratoListItem:
    return ContratoListItem(
        id=c.id,
        codigo=c.codigo,
        tipo_codigo=c.tipo_codigo,
        proveedor_contratista=c.proveedor_contratista,
        nit_proveedor=c.nit_proveedor,
        valor=c.valor,
        moneda=c.moneda,
        plazo_cantidad=c.plazo_cantidad,
        plazo_unidad=c.plazo_unidad,
        renovacion_automatica=c.renovacion_automatica,
        requiere_poliza=c.requiere_poliza,
        tiene_poliza=c.tiene_poliza(),
        tiene_borrador=c.tiene_borrador(),
        cantidad_otrosies=c.cantidad_otrosies(),
        estado_aprobacion=c.estado_aprobacion,
        estado=c.estado,
        fecha_inicio=c.fecha_inicio,
        fecha_fin=c.fecha_fin,
        fecha_proxima_notificacion=c.fecha_proxima_notificacion,
        hora_proxima_notificacion=c.hora_proxima_notificacion,
        eliminado_at=c.eliminado_at,
        eliminado_por_id=c.eliminado_por_id,
        eliminado_observacion=c.eliminado_observacion,
        dias_para_vencer=_dias_para_vencer(c),
        alerta_vencimiento=_alerta_vencimiento(c),
        created_at=c.created_at,
    )


def _to_otrosi_pendiente_response(contrato, otrosi) -> OtrosiPendienteResponse:
    return OtrosiPendienteResponse(
        contrato=_to_contrato_response(contrato),
        contrato_id=contrato.id,
        otrosi=_to_otrosi_response(otrosi),
    )


def _emails_desde_cadena(valor: str) -> list[str]:
    return [email.strip() for email in (valor or "").split(",") if email.strip()]


def _validate_and_read(
    upload: Optional[UploadFile], tipo: TipoArchivo, requerido: bool
) -> Optional[ArchivoEntrada]:
    if upload is None or upload.filename in (None, ""):
        if requerido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Falta el archivo obligatorio: {tipo.value}",
            )
        return None
    contenido = upload.file.read()
    if len(contenido) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"El archivo '{upload.filename}' supera el límite de "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )
    return ArchivoEntrada(
        tipo=tipo,
        nombre_original=upload.filename,
        mime_type=upload.content_type or "application/octet-stream",
        contenido=contenido,
    )


@router.post("", response_model=ContratoResponse, status_code=status.HTTP_201_CREATED)
def radicar_solicitud(
    background_tasks: BackgroundTasks,
    proveedor_contratista: str = Form(...),
    tipo_codigo: str = Form("C"),
    nit_proveedor: str = Form(...),
    descripcion_servicio: str = Form(...),
    obligaciones_colbeef: str = Form(...),
    obligaciones_proveedor: str = Form(...),
    valor: str = Form(..., description="Valor numérico del contrato."),
    moneda: Moneda = Form(...),
    plazo_cantidad: int = Form(...),
    plazo_unidad: UnidadPlazo = Form(...),
    fecha_inicio: Optional[date] = Form(None),
    fecha_fin: Optional[date] = Form(None),
    fecha_proxima_notificacion: Optional[date] = Form(None),
    renovacion_automatica: bool = Form(...),
    condiciones_recibido_satisfactorio: str = Form(...),
    requiere_poliza: bool = Form(...),
    correo_lider_proceso: str = Form(...),
    correo_gerencia: str = Form(...),
    camara_comercio: UploadFile = File(..., description="PDF/Imagen — obligatorio"),
    cotizacion: UploadFile = File(..., description="PDF/Imagen — obligatorio"),
    cedula_rep_legal: UploadFile = File(..., description="PDF/Imagen — obligatorio"),
    archivo_opcional: Optional[UploadFile] = File(None, description="Cualquier archivo"),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> ContratoResponse:
    try:
        valor_decimal = Decimal(valor)
    except (InvalidOperation, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El valor del contrato no es un número válido.",
        )
    if current.is_compras() and (
        fecha_inicio is not None
        or fecha_fin is not None
        or fecha_proxima_notificacion is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compras no puede asignar fechas de vigencia ni notificación. Eso lo define Jurídica.",
        )

    archivos: list[ArchivoEntrada] = []
    for upload, tipo, requerido in [
        (camara_comercio, TipoArchivo.CAMARA_COMERCIO, True),
        (cotizacion, TipoArchivo.COTIZACION, True),
        (cedula_rep_legal, TipoArchivo.CEDULA_REP_LEGAL, True),
        (archivo_opcional, TipoArchivo.OPCIONAL, False),
    ]:
        entrada = _validate_and_read(upload, tipo, requerido)
        if entrada is not None:
            archivos.append(entrada)

    try:
        contrato = RadicarSolicitud(contratos, storage).execute(
            actor=current,
            proveedor_contratista=proveedor_contratista,
            nit_proveedor=nit_proveedor,
            descripcion_servicio=descripcion_servicio,
            obligaciones_colbeef=obligaciones_colbeef,
            obligaciones_proveedor=obligaciones_proveedor,
            valor=valor_decimal,
            moneda=moneda,
            plazo_cantidad=plazo_cantidad,
            plazo_unidad=plazo_unidad,
            renovacion_automatica=renovacion_automatica,
            condiciones_recibido_satisfactorio=condiciones_recibido_satisfactorio,
            requiere_poliza=requiere_poliza,
            correo_lider_proceso=correo_lider_proceso.strip(),
            correo_gerencia=correo_gerencia.strip() or settings.GERENCIA_EMAIL.strip(),
            tipo_codigo=tipo_codigo,
            archivos=archivos,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            fecha_proxima_notificacion=fecha_proxima_notificacion,
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except MissingRequiredFileError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Paso 1: el correo va al líder de proceso para aprobación.
    destinatarios = [contrato.correo_lider_proceso]
    if destinatarios:
        background_tasks.add_task(
            NotificarRadicacion(notifier).execute,
            contrato,
            current.username,
            destinatarios,
            _approval_token(contrato.id, "lider"),
        )

    return _to_contrato_response(contrato)


@router.get("", response_model=list[ContratoListItem])
def list_contratos_endpoint(
    q: Optional[str] = Query(
        None, description="Búsqueda por código (ej. C-0001 u OS-0001), proveedor o NIT."
    ),
    estado: Optional[EstadoContrato] = Query(
        None, description="Filtrar por estado del contrato."
    ),
    eliminados: bool = Query(False, description="Ver contratos eliminados."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> list[ContratoListItem]:
    items = BuscarContratos(contratos).execute(
        actor=current,
        query=q,
        estado=estado,
        eliminados=eliminados,
    )
    return [_to_list_item(c) for c in items]


@router.get("/otrosies/pendientes", response_model=list[OtrosiPendienteResponse])
def list_otrosies_pendientes(
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> list[OtrosiPendienteResponse]:
    if not (current.is_admin() or current.is_juridica()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo Jurídica o Admin pueden ver otrosíes pendientes.",
        )
    items = contratos.list_otrosies_by_estado_aprobacion(EstadoAprobacion.APROBADO)
    return [
        _to_otrosi_pendiente_response(c, o)
        for c, o in items
        if o.archivo_id is None and o.aprobado_gerencia_at is not None
    ]


@router.get("/seguimiento/publico", response_model=SeguimientoContratoResponse)
def seguimiento_publico_contrato(
    codigo: str = Query(..., description="Código del contrato, ej. C-0001 u OS-0001."),
    token: str = Query(..., description="Token recibido por correo."),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> SeguimientoContratoResponse:
    contrato = contratos.get_by_codigo(codigo.strip().upper())
    if contrato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un contrato con ese código.",
        )
    if not _validar_token_seguimiento(contrato.id, token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El enlace de seguimiento no es válido para este contrato.",
        )
    if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El seguimiento estará disponible cuando Gerencia apruebe "
                "y el contrato pase a Jurídica."
            ),
        )
    return SeguimientoContratoResponse(
        codigo=contrato.codigo or "",
        tipo_codigo=contrato.tipo_codigo,
        proveedor_contratista=contrato.proveedor_contratista,
        estado_aprobacion=contrato.estado_aprobacion,
        estado=contrato.estado,
        creado_en=contrato.created_at,
        aprobado_lider_at=contrato.aprobado_lider_at,
        aprobado_gerencia_at=contrato.aprobado_gerencia_at,
        tiene_poliza=contrato.tiene_poliza(),
        tiene_borrador=contrato.tiene_borrador(),
        requiere_poliza=contrato.requiere_poliza,
    )


@router.get("/{contrato_id}", response_model=ContratoResponse)
def get_contrato(
    contrato_id: int,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> ContratoResponse:
    try:
        contrato = GetContrato(contratos).execute(actor=current, contrato_id=contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _to_contrato_response(contrato)


@router.delete("/{contrato_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_contrato(
    contrato_id: int,
    observacion: str = Query(..., min_length=1, description="Motivo de eliminación."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> None:
    if not (current.is_admin() or current.is_juridica()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo Jurídica o Admin pueden eliminar contratos.",
        )
    contrato = contratos.get_by_id(contrato_id)
    if contrato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el contrato {contrato_id}.",
        )
    if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este contrato todavía no tiene aprobación de líder y gerencia.",
        )
    observacion = (observacion or "").strip()
    if not observacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La observación de eliminación es obligatoria.",
        )
    eliminado = contratos.delete(
        contrato_id,
        eliminado_por_id=current.id,
        observacion=observacion,
    )
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el contrato {contrato_id}.",
        )


@router.get("/{contrato_id}/revision/{paso}", response_class=HTMLResponse)
def revisar_solicitud_por_correo(
    contrato_id: int,
    paso: str,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> HTMLResponse:
    if paso not in ("lider", "gerencia") or not _validar_token(contrato_id, paso, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")

    contrato = contratos.get_by_id(contrato_id)
    if contrato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el contrato {contrato_id}.",
        )

    aprobar_url = f"/api/v1/contratos/{contrato_id}/aprobar/{paso}?token={token}"
    rechazar_url = f"/api/v1/contratos/{contrato_id}/rechazar/{paso}?token={token}"
    paso_label = "Líder de proceso" if paso == "lider" else "Gerencia"
    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>Revisión solicitud {escape(contrato.codigo or '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; background:#f5f7fb; margin:0; padding:24px; color:#0f172a; }}
                .wrap {{ max-width: 920px; margin: 0 auto; background:white; border:1px solid #e2e8f0; border-radius:12px; overflow:hidden; }}
                .header {{ background:#1f4e8a; color:white; padding:22px 28px; }}
                .content {{ padding:28px; }}
                h1, h2 {{ margin:0 0 10px; }}
                h3 {{ color:#163966; border-bottom:1px solid #e2e8f0; padding-bottom:6px; margin-top:24px; }}
                .codigo {{ display:inline-block; background:#e8f0fb; color:#163966; font-weight:700; padding:6px 12px; border-radius:6px; }}
                .grid {{ display:grid; grid-template-columns: 220px 1fr; gap:8px 16px; margin:14px 0; }}
                .label {{ color:#64748b; font-weight:600; }}
                .value {{ white-space:pre-wrap; }}
                .actions {{ display:flex; gap:12px; margin-top:28px; padding-top:20px; border-top:1px solid #e2e8f0; }}
                .btn {{ display:inline-block; text-decoration:none; color:white; padding:12px 22px; border-radius:8px; font-weight:700; }}
                .approve {{ background:#166534; }}
                .reject {{ background:#991b1b; }}
                .warn {{ background:#fff7ed; color:#92400e; border-left:4px solid #d97706; padding:12px; border-radius:6px; }}
            </style>
        </head>
        <body>
            <div class="wrap">
                <div class="header">
                    <h1>JURICOM_BEEF</h1>
                    <p>Revisión de solicitud por {escape(paso_label)}</p>
                </div>
                <div class="content">
                    <h2>Solicitud de contrato <span class="codigo">{escape(contrato.codigo or '')}</span></h2>
                    <p class="warn">
                        Revisa la información completa. Si todo está correcto, aprueba.
                        Si encuentras errores o falta información, rechaza la solicitud.
                    </p>

                    <h3>Información general</h3>
                    <div class="grid">
                        <div class="label">Compañía</div><div>{escape(contrato.compania)}</div>
                        <div class="label">Proveedor / Contratista</div><div>{escape(contrato.proveedor_contratista)}</div>
                        <div class="label">NIT</div><div>{escape(contrato.nit_proveedor)}</div>
                        <div class="label">Valor</div><div>{escape(str(contrato.valor))} {escape(contrato.moneda.value)}</div>
                        <div class="label">Plazo</div><div>{contrato.plazo_cantidad} {escape(contrato.plazo_unidad.value)}</div>
                        <div class="label">Renovación automática</div><div>{'Sí' if contrato.renovacion_automatica else 'No'}</div>
                        <div class="label">Requiere póliza</div><div>{'Sí' if contrato.requiere_poliza else 'No'}</div>
                        <div class="label">Correo líder proceso</div><div>{escape(contrato.correo_lider_proceso)}</div>
                        <div class="label">Correo gerencia</div><div>{escape(contrato.correo_gerencia)}</div>
                        <div class="label">Estado aprobación</div><div>{escape(contrato.estado_aprobacion.value)}</div>
                    </div>

                    <h3>Descripción del servicio</h3>
                    <div class="value">{escape(contrato.descripcion_servicio)}</div>

                    <h3>Obligaciones de Colbeef</h3>
                    <div class="value">{escape(contrato.obligaciones_colbeef)}</div>

                    <h3>Obligaciones del proveedor</h3>
                    <div class="value">{escape(contrato.obligaciones_proveedor)}</div>

                    <h3>Condiciones de recibido satisfactorio</h3>
                    <div class="value">{escape(contrato.condiciones_recibido_satisfactorio)}</div>

                    <h3>Archivos adjuntos</h3>
                    <ul>
                        {''.join(
                            f'<li><strong>{escape(a.tipo.value)}</strong>: '
                            f'<a href="/api/v1/contratos/{contrato_id}/revision/{paso}/archivo/{a.id}?token={escape(token)}">'
                            f'Descargar {escape(a.nombre_original)}</a></li>'
                            for a in contrato.archivos
                        )}
                    </ul>

                    <div class="actions">
                        <a class="btn approve" href="{aprobar_url}">Aprobar solicitud</a>
                        <a class="btn reject" href="{rechazar_url}">Rechazar solicitud</a>
                    </div>
                </div>
            </div>
        </body>
        </html>"""
    )


@router.get("/{contrato_id}/revision/{paso}/archivo/{archivo_id}")
def descargar_archivo_revision(
    contrato_id: int,
    paso: str,
    archivo_id: int,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
):
    if paso not in ("lider", "gerencia") or not _validar_token(contrato_id, paso, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")

    contrato = contratos.get_by_id(contrato_id)
    if contrato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el contrato {contrato_id}.",
        )
    archivo = next((a for a in contrato.archivos if a.id == archivo_id), None)
    if archivo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado."
        )
    ruta_completa = settings.upload_dir_path / archivo.ruta_almacenamiento
    if not ruta_completa.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="El archivo ya no está disponible en disco.",
        )
    return FileResponse(
        path=str(ruta_completa),
        media_type=archivo.mime_type,
        filename=archivo.nombre_original,
        content_disposition_type="attachment",
    )


@router.get("/{contrato_id}/aprobar/{paso}", response_class=HTMLResponse)
def aprobar_por_correo(
    contrato_id: int,
    paso: str,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> HTMLResponse:
    if paso not in ("lider", "gerencia") or not _validar_token(contrato_id, paso, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")

    try:
        caso = AprobarContrato(contratos)
        if paso == "lider":
            contrato = caso.aprobar_lider(contrato_id)
            _notificar_gerencia_aprobacion(contrato, notifier)
            mensaje = (
                "Aprobación del líder registrada. "
                "Ahora se notificó a Gerencia para la aprobación final."
            )
        else:
            contrato = caso.aprobar_gerencia(contrato_id)
            _notificar_juridica_aprobado(contrato, notifier)
            _notificar_lider_contrato_en_juridica(contrato, notifier)
            mensaje = (
                "Aprobación de Gerencia registrada. "
                "El contrato ya aparece para Jurídica en el módulo Contratos."
            )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        contrato = contratos.get_by_id(contrato_id)
        if contrato is not None:
            return _html_aprobacion_ya_procesada(contrato, paso, str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Contrato aprobado</title></head>
        <body style="font-family: Arial, sans-serif; padding: 32px;">
            <h1 style="color:#1f4e8a;">JURICOM_BEEF</h1>
            <h2>{mensaje}</h2>
            <p>Contrato <strong>{contrato.codigo}</strong> - {contrato.proveedor_contratista}</p>
            <p>Ya puedes cerrar esta ventana.</p>
        </body>
        </html>"""
    )


@router.get("/{contrato_id}/rechazar/{paso}", response_class=HTMLResponse)
def rechazar_por_correo(
    contrato_id: int,
    paso: str,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> HTMLResponse:
    if paso not in ("lider", "gerencia") or not _validar_token(contrato_id, paso, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")

    try:
        contrato = AprobarContrato(contratos).rechazar(contrato_id, paso)
        mensaje = (
            "Solicitud rechazada por el líder de proceso."
            if paso == "lider"
            else "Solicitud rechazada por Gerencia."
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Solicitud rechazada</title></head>
        <body style="font-family: Arial, sans-serif; padding: 32px;">
            <h1 style="color:#1f4e8a;">JURICOM_BEEF</h1>
            <h2>{escape(mensaje)}</h2>
            <p>Contrato <strong>{escape(contrato.codigo or '')}</strong> - {escape(contrato.proveedor_contratista)}</p>
            <p>La solicitud quedó marcada como <strong>rechazada</strong> y no pasará a Jurídica.</p>
            <p>Ya puedes cerrar esta ventana.</p>
        </body>
        </html>"""
    )


def _html_aprobacion_ya_procesada(contrato, paso: str, detalle: str) -> HTMLResponse:
    if contrato.estado_aprobacion == EstadoAprobacion.APROBADO:
        mensaje = "Este contrato ya fue aprobado por Gerencia y enviado a Jurídica."
    elif (
        paso == "lider"
        and contrato.estado_aprobacion == EstadoAprobacion.PENDIENTE_GERENCIA
    ):
        mensaje = "El líder ya aprobó este contrato. Ahora está pendiente de Gerencia."
    elif contrato.estado_aprobacion == EstadoAprobacion.RECHAZADO:
        mensaje = "Esta solicitud ya fue rechazada."
    else:
        mensaje = detalle

    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Aprobación ya procesada</title></head>
        <body style="font-family: Arial, sans-serif; padding: 32px;">
            <h1 style="color:#1f4e8a;">JURICOM_BEEF</h1>
            <h2>{escape(mensaje)}</h2>
            <p>Contrato <strong>{escape(contrato.codigo or '')}</strong> - {escape(contrato.proveedor_contratista)}</p>
            <p>Ya puedes cerrar esta ventana.</p>
        </body>
        </html>"""
    )


def _notificar_gerencia_aprobacion(contrato, notifier: EmailNotifier) -> None:
    destinatarios = _emails_desde_cadena(contrato.correo_gerencia)
    if not notifier.disponible or not destinatarios:
        return
    from app.infrastructure.email.templates import (
        render_aprobacion_gerencia_html,
        render_aprobacion_gerencia_texto,
    )

    token = _approval_token(contrato.id, "gerencia")
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] Aprobación Gerencia — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=render_aprobacion_gerencia_html(contrato, token),
            cuerpo_texto=render_aprobacion_gerencia_texto(contrato, token),
        )
    )


def _notificar_juridica_aprobado(contrato, notifier: EmailNotifier) -> None:
    destinatarios = settings.juridica_emails_list
    if not notifier.disponible or not destinatarios:
        return
    from app.infrastructure.email.templates import (
        render_aprobado_juridica_html,
        render_aprobado_juridica_texto,
    )

    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] Contrato pendiente por revisar — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=render_aprobado_juridica_html(contrato),
            cuerpo_texto=render_aprobado_juridica_texto(contrato),
        )
    )


def _notificar_lider_contrato_en_juridica(contrato, notifier: EmailNotifier) -> None:
    if not notifier.disponible or not contrato.correo_lider_proceso:
        return
    from app.infrastructure.email.templates import (
        render_seguimiento_lider_juridica_html,
        render_seguimiento_lider_juridica_texto,
    )

    token = _approval_token(contrato.id, "lider")
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] Contrato en Jurídica — {contrato.codigo}",
            destinatarios=[contrato.correo_lider_proceso],
            cuerpo_html=render_seguimiento_lider_juridica_html(contrato, token),
            cuerpo_texto=render_seguimiento_lider_juridica_texto(contrato, token),
        )
    )


@router.put("/{contrato_id}/estado", response_model=ContratoResponse)
def cambiar_estado(
    contrato_id: int,
    payload: CambiarEstadoRequest,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> ContratoResponse:
    try:
        contrato = CambiarEstadoContrato(contratos).execute(
            actor=current, contrato_id=contrato_id, nuevo_estado=payload.estado
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_contrato_response(contrato)


@router.put("/{contrato_id}", response_model=ContratoResponse)
def editar_contrato(
    contrato_id: int,
    payload: EditarContratoRequest,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> ContratoResponse:
    try:
        contrato = EditarContrato(contratos).execute(
            actor=current,
            contrato_id=contrato_id,
            proveedor_contratista=payload.proveedor_contratista,
            nit_proveedor=payload.nit_proveedor,
            descripcion_servicio=payload.descripcion_servicio,
            obligaciones_colbeef=payload.obligaciones_colbeef,
            obligaciones_proveedor=payload.obligaciones_proveedor,
            valor=payload.valor,
            moneda=payload.moneda,
            plazo_cantidad=payload.plazo_cantidad,
            plazo_unidad=payload.plazo_unidad,
            renovacion_automatica=payload.renovacion_automatica,
            condiciones_recibido_satisfactorio=payload.condiciones_recibido_satisfactorio,
            requiere_poliza=payload.requiere_poliza,
            fecha_inicio=payload.fecha_inicio,
            fecha_fin=payload.fecha_fin,
            fecha_proxima_notificacion=payload.fecha_proxima_notificacion,
            hora_proxima_notificacion=payload.hora_proxima_notificacion,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_contrato_response(contrato)


def _adjuntar_archivo_juridica(
    contrato_id: int,
    tipo: TipoArchivo,
    upload: UploadFile,
    current: User,
    contratos: ContratoRepository,
    storage: FileStorage,
) -> ArchivoResponse:
    if upload is None or not upload.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes adjuntar un archivo.",
        )
    contenido = upload.file.read()
    if len(contenido) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )

    entrada = ArchivoJuridicaEntrada(
        tipo=tipo,
        nombre_original=upload.filename,
        mime_type=upload.content_type or "application/octet-stream",
        contenido=contenido,
    )
    try:
        archivo = AdjuntarArchivoJuridica(contratos, storage).execute(
            actor=current, contrato_id=contrato_id, entrada=entrada
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidFileError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_archivo_response(archivo)


@router.post("/{contrato_id}/poliza", response_model=ArchivoResponse)
def subir_poliza(
    contrato_id: int,
    archivo: UploadFile = File(..., description="PDF de la póliza."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> ArchivoResponse:
    return _adjuntar_archivo_juridica(
        contrato_id, TipoArchivo.POLIZA, archivo, current, contratos, storage
    )


@router.post("/{contrato_id}/borrador", response_model=ArchivoResponse)
def subir_borrador(
    contrato_id: int,
    archivo: UploadFile = File(..., description="PDF del contrato firmado (borrador)."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> ArchivoResponse:
    return _adjuntar_archivo_juridica(
        contrato_id, TipoArchivo.BORRADOR_FIRMADO, archivo, current, contratos, storage
    )


@router.post("/{contrato_id}/otrosi", response_model=ContratoResponse)
def aplicar_otrosi(
    contrato_id: int,
    tipo: TipoOtrosi = Form(..., description="prorroga | adicion | modificacion | otro"),
    descripcion: str = Form(..., description="Motivo / descripción del otrosí."),
    plazo_adicional_cantidad: Optional[int] = Form(
        None, description="Sólo para prórroga. Cantidad en la misma unidad del contrato."
    ),
    valor_adicional: Optional[Decimal] = Form(
        None, description="Sólo para adición. Valor adicional en la moneda del contrato."
    ),
    nueva_descripcion_servicio: Optional[str] = Form(
        None, description="Sólo para modificación. Nuevo texto de la descripción."
    ),
    archivo: Optional[UploadFile] = File(
        None, description="PDF del otrosí firmado (opcional)."
    ),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> ContratoResponse:
    archivo_input: Optional[ArchivoOtrosi] = None
    if archivo is not None and archivo.filename:
        contenido = archivo.file.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB."
                ),
            )
        archivo_input = ArchivoOtrosi(
            nombre_original=archivo.filename,
            mime_type=archivo.content_type or "application/pdf",
            contenido=contenido,
        )

    try:
        resultado = AplicarOtrosi(contratos, storage).execute(
            actor=current,
            contrato_id=contrato_id,
            tipo=tipo,
            descripcion=descripcion,
            plazo_adicional_cantidad=plazo_adicional_cantidad,
            valor_adicional=valor_adicional,
            nueva_descripcion_servicio=nueva_descripcion_servicio,
            archivo=archivo_input,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidContratoStateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if current.is_compras():
        _notificar_solicitud_otrosi(resultado.contrato, resultado.otrosi, current, notifier)

    return _to_contrato_response(resultado.contrato)


@router.get("/{contrato_id}/otrosi/{otrosi_id}/aprobar/{paso}", response_class=HTMLResponse)
def aprobar_otrosi_por_correo(
    contrato_id: int,
    otrosi_id: int,
    paso: str,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> HTMLResponse:
    if paso not in ("lider", "gerencia") or not _validar_otrosi_token(
        contrato_id, otrosi_id, paso, token
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")

    contrato = contratos.get_by_id(contrato_id)
    otrosi = contratos.get_otrosi(otrosi_id)
    if contrato is None or otrosi is None or otrosi.contrato_id != contrato_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Otrosí no existe.")

    if paso == "lider":
        if otrosi.estado_aprobacion != EstadoAprobacion.PENDIENTE_LIDER:
            mensaje = "Esta solicitud de otrosí ya fue procesada por el líder."
        else:
            otrosi.estado_aprobacion = EstadoAprobacion.PENDIENTE_GERENCIA
            otrosi.aprobado_lider_at = datetime.now()
            otrosi = contratos.update_otrosi(otrosi)
            _notificar_gerencia_otrosi(contrato, otrosi, notifier)
            mensaje = "Aprobación del líder registrada. Se notificó a Gerencia."
    else:
        if otrosi.estado_aprobacion != EstadoAprobacion.PENDIENTE_GERENCIA:
            mensaje = "Esta solicitud de otrosí no está pendiente de Gerencia."
        else:
            otrosi.estado_aprobacion = EstadoAprobacion.APROBADO
            otrosi.aprobado_gerencia_at = datetime.now()
            otrosi = contratos.update_otrosi(otrosi)
            _notificar_juridica_otrosi_pendiente(contrato, otrosi, notifier)
            mensaje = (
                "Aprobación de Gerencia registrada. "
                "El otrosí quedó pendiente para Jurídica."
            )

    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es"><head><meta charset="UTF-8"><title>Otrosí aprobado</title></head>
        <body style="font-family:Arial;padding:32px;">
            <h2>JURICOM_BEEF</h2>
            <p>{escape(mensaje)}</p>
            <p>Contrato: <strong>{escape(contrato.codigo or '')}</strong></p>
        </body></html>"""
    )


@router.get("/{contrato_id}/otrosi/{otrosi_id}/rechazar/{paso}", response_class=HTMLResponse)
def rechazar_otrosi_por_correo(
    contrato_id: int,
    otrosi_id: int,
    paso: str,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> HTMLResponse:
    if paso not in ("lider", "gerencia") or not _validar_otrosi_token(
        contrato_id, otrosi_id, paso, token
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")
    contrato = contratos.get_by_id(contrato_id)
    otrosi = contratos.get_otrosi(otrosi_id)
    if contrato is None or otrosi is None or otrosi.contrato_id != contrato_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Otrosí no existe.")

    otrosi.estado_aprobacion = EstadoAprobacion.RECHAZADO
    contratos.update_otrosi(otrosi)
    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es"><head><meta charset="UTF-8"><title>Otrosí rechazado</title></head>
        <body style="font-family:Arial;padding:32px;">
            <h2>JURICOM_BEEF</h2>
            <p>Solicitud de otrosí rechazada por {escape(paso)}.</p>
            <p>Contrato: <strong>{escape(contrato.codigo or '')}</strong></p>
        </body></html>"""
    )


@router.post("/{contrato_id}/otrosi/{otrosi_id}/finalizar", response_model=ContratoResponse)
def finalizar_otrosi_juridica(
    contrato_id: int,
    otrosi_id: int,
    tipo: TipoOtrosi = Form(...),
    descripcion: str = Form(...),
    plazo_adicional_cantidad: Optional[int] = Form(None),
    valor_adicional: Optional[Decimal] = Form(None),
    nueva_descripcion_servicio: Optional[str] = Form(None),
    archivo: UploadFile = File(..., description="PDF firmado del otrosí."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> ContratoResponse:
    if not (current.is_admin() or current.is_juridica()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo Jurídica o Admin pueden finalizar otrosíes.",
        )
    contrato = contratos.get_by_id(contrato_id)
    otrosi = contratos.get_otrosi(otrosi_id)
    if contrato is None or otrosi is None or otrosi.contrato_id != contrato_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Otrosí no existe.")
    if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este contrato todavía no tiene aprobación de líder y gerencia.",
        )
    if otrosi.estado_aprobacion != EstadoAprobacion.APROBADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El otrosí debe estar aprobado por líder y Gerencia.",
        )
    if otrosi.archivo_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este otrosí ya tiene contrato firmado cargado.",
        )

    try:
        _actualizar_datos_otrosi(
            otrosi,
            contrato,
            tipo,
            descripcion,
            plazo_adicional_cantidad,
            valor_adicional,
            nueva_descripcion_servicio,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    contenido = archivo.file.read()
    if len(contenido) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    stored = storage.save(
        contenido=contenido,
        nombre_original=archivo.filename,
        mime_type=archivo.content_type or "application/pdf",
        subcarpeta="contratos",
    )
    archivo_creado = contratos.add_archivo(
        ArchivoAdjunto(
            tipo=TipoArchivo.OTROSI,
            nombre_original=stored.nombre_original,
            ruta_almacenamiento=stored.ruta,
            mime_type=stored.mime_type,
            tamano_bytes=stored.tamano_bytes,
            contrato_id=contrato_id,
            subido_por_id=current.id,
        )
    )
    otrosi.archivo_id = archivo_creado.id

    _aplicar_cambios_otrosi_al_contrato(contrato, otrosi)
    contratos.update(contrato)
    contratos.update_otrosi(otrosi)
    final = contratos.get_by_id(contrato_id)
    return _to_contrato_response(final)


def _actualizar_datos_otrosi(
    otrosi,
    contrato,
    tipo: TipoOtrosi,
    descripcion: str,
    plazo_adicional_cantidad: Optional[int],
    valor_adicional: Optional[Decimal],
    nueva_descripcion_servicio: Optional[str],
) -> None:
    descripcion = (descripcion or "").strip()
    if not descripcion:
        raise ValueError("La descripción / motivo del otrosí es obligatoria.")

    otrosi.tipo = tipo
    otrosi.descripcion = descripcion
    otrosi.plazo_adicional_cantidad = None
    otrosi.plazo_adicional_unidad = None
    otrosi.valor_adicional = None
    otrosi.nueva_descripcion_servicio = None

    if tipo == TipoOtrosi.PRORROGA:
        if not plazo_adicional_cantidad or plazo_adicional_cantidad <= 0:
            raise ValueError("Para una prórroga debes indicar plazo adicional mayor a 0.")
        otrosi.plazo_adicional_cantidad = plazo_adicional_cantidad
        otrosi.plazo_adicional_unidad = contrato.plazo_unidad
    elif tipo == TipoOtrosi.ADICION:
        if valor_adicional is None or Decimal(valor_adicional) <= 0:
            raise ValueError("Para una adición debes indicar valor adicional mayor a 0.")
        otrosi.valor_adicional = Decimal(valor_adicional)
    elif tipo == TipoOtrosi.MODIFICACION:
        if not nueva_descripcion_servicio or not nueva_descripcion_servicio.strip():
            raise ValueError("Para una modificación debes indicar la nueva descripción.")
        otrosi.nueva_descripcion_servicio = nueva_descripcion_servicio.strip()
    elif tipo == TipoOtrosi.OTRO:
        # "Otro" es flexible: Jurídica puede modificar plazo, valor y/o descripción.
        if plazo_adicional_cantidad and plazo_adicional_cantidad > 0:
            otrosi.plazo_adicional_cantidad = plazo_adicional_cantidad
            otrosi.plazo_adicional_unidad = contrato.plazo_unidad
        if valor_adicional is not None and Decimal(valor_adicional) > 0:
            otrosi.valor_adicional = Decimal(valor_adicional)
        if nueva_descripcion_servicio and nueva_descripcion_servicio.strip():
            otrosi.nueva_descripcion_servicio = nueva_descripcion_servicio.strip()


def _aplicar_cambios_otrosi_al_contrato(contrato, otrosi) -> None:
    if otrosi.plazo_adicional_cantidad is not None:
        contrato.plazo_cantidad += otrosi.plazo_adicional_cantidad
    if otrosi.valor_adicional is not None:
        contrato.valor = (contrato.valor or Decimal("0")) + Decimal(otrosi.valor_adicional)
    if otrosi.nueva_descripcion_servicio:
        contrato.descripcion_servicio = otrosi.nueva_descripcion_servicio


def _notificar_solicitud_otrosi(contrato, otrosi, current: User, notifier: EmailNotifier) -> None:
    destinatarios = [contrato.correo_lider_proceso] if contrato.correo_lider_proceso else []
    if not notifier.disponible or not destinatarios:
        return
    from app.infrastructure.email.templates import (
        render_solicitud_otrosi_html,
        render_solicitud_otrosi_texto,
    )
    token = _otrosi_approval_token(contrato.id, otrosi.id, "lider")

    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] Solicitud de otrosí — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=render_solicitud_otrosi_html(
                contrato, otrosi, current.username, token
            ),
            cuerpo_texto=render_solicitud_otrosi_texto(
                contrato, otrosi, current.username, token
            ),
        )
    )


def _notificar_gerencia_otrosi(contrato, otrosi, notifier: EmailNotifier) -> None:
    destinatarios = _emails_desde_cadena(contrato.correo_gerencia)
    if not notifier.disponible or not destinatarios:
        return
    from app.infrastructure.email.templates import (
        render_aprobacion_gerencia_otrosi_html,
        render_aprobacion_gerencia_otrosi_texto,
    )

    token = _otrosi_approval_token(contrato.id, otrosi.id, "gerencia")
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] Aprobación Gerencia otrosí — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=render_aprobacion_gerencia_otrosi_html(contrato, otrosi, token),
            cuerpo_texto=render_aprobacion_gerencia_otrosi_texto(contrato, otrosi, token),
        )
    )


def _notificar_juridica_otrosi_pendiente(contrato, otrosi, notifier: EmailNotifier) -> None:
    destinatarios = settings.juridica_emails_list
    if not notifier.disponible or not destinatarios:
        return
    from app.infrastructure.email.templates import (
        render_otrosi_pendiente_juridica_html,
        render_otrosi_pendiente_juridica_texto,
    )

    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM_BEEF] Otrosí pendiente Jurídica — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=render_otrosi_pendiente_juridica_html(contrato, otrosi),
            cuerpo_texto=render_otrosi_pendiente_juridica_texto(contrato, otrosi),
        )
    )
