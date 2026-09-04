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
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.application.services.aprobacion_gerencia import correo_aprobacion_gerencia
from app.application.services.trazabilidad_contrato_srv import (
    etapa_historial_contrato,
    etiqueta_estado_contrato,
    registrar_evento_contrato_en_srv,
    registrar_observacion_contrato_en_srv,
)
from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.email_notifier import (
    EmailAttachment,
    EmailMessage,
    EmailNotifier,
)
from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.user_repository import UserRepository
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.use_cases.contratos import (
    AdjuntarArchivoJuridica,
    AplicarOtrosi,
    AprobarContrato,
    ArchivoEntrada,
    ArchivoFinalizacion,
    ArchivoJuridicaEntrada,
    ArchivoOtrosi,
    BuscarContratos,
    CambiarEstadoContrato,
    ConfirmarPagoTesoreria,
    ConfirmarCierreTesoreria,
    GestionarCierreContabilidad,
    ArchivoRespuesta,
    CargarActaLiquidacion,
    EditarContrato,
    EnviarAnticipoContabilidad,
    FinalizarContratoCompras,
    GestionarAnticipoContabilidad,
    GetContrato,
    RadicarSolicitud,
    ResponderInformacion,
    SolicitarInformacion,
)
from app.application.use_cases.contratos.solicitar_informacion import ArchivoSolicitudInfo
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
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_otrosi import TipoOtrosi
from app.domain.value_objects.tipo_precio import TipoPrecio
from app.domain.value_objects.unidad_plazo import UnidadPlazo
from app.infrastructure.config import settings
from app.infrastructure.minutas.generator import PLANTILLAS, generar_minuta
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
    get_email_notifier,
    get_file_storage,
    get_solicitud_gestion_repository,
    get_user_repository,
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
    SolicitudInformacionResponse,
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


def _alerta_elaboracion(c) -> bool:
    """Urgente cuando el plazo de elaboración vence hoy/mañana o ya venció."""
    dias = c.dias_para_elaborar()
    return dias is not None and dias <= 1


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
        solicitud_gestion_id=c.solicitud_gestion_id,
        solicitud_gestion_codigo=c.solicitud_gestion_codigo or "",
        compania=c.compania,
        proveedor_contratista=c.proveedor_contratista,
        nit_proveedor=c.nit_proveedor,
        proveedor_email=getattr(c, "proveedor_email", "") or "",
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
        tipo_precio=c.tipo_precio,
        forma_pago=c.forma_pago or "",
        centro_costos=c.centro_costos or "",
        supervisor_id=c.supervisor_id,
        supervisor_username=c.supervisor_username or "",
        requiere_anticipo=bool(getattr(c, "requiere_anticipo", False)),
        porcentaje_anticipo=getattr(c, "porcentaje_anticipo", None),
        monto_anticipo=getattr(c, "monto_anticipo", None),
        observaciones_anticipo=getattr(c, "observaciones_anticipo", "") or "",
        anticipo_pagado=bool(getattr(c, "anticipo_pagado", False)),
        correo_lider_proceso=c.correo_lider_proceso,
        correo_gerencia=c.correo_gerencia,
        estado_aprobacion=c.estado_aprobacion,
        fecha_inicio=c.fecha_inicio,
        fecha_inicio_original=c.fecha_inicio_original,
        fecha_fin=c.fecha_fin,
        fecha_limite_elaboracion=c.fecha_limite_elaboracion_efectiva(),
        dias_para_elaborar=c.dias_para_elaborar(),
        alerta_elaboracion=_alerta_elaboracion(c),
        fecha_proxima_notificacion=c.fecha_proxima_notificacion,
        hora_proxima_notificacion=c.hora_proxima_notificacion,
        estado=c.estado,
        creado_por_id=c.creado_por_id,
        tiene_poliza=c.tiene_poliza(),
        tiene_borrador=c.tiene_borrador(),
        requiere_acta_liquidacion=c.requiere_acta_liquidacion(_umbral_acta()),
        tiene_informe_final=c.tiene_informe_final(),
        tiene_acta_liquidacion=c.tiene_acta_liquidacion(),
        pendiente_acta_liquidacion=c.esperando_acta_liquidacion(_umbral_acta()),
        eliminado_at=c.eliminado_at,
        eliminado_por_id=c.eliminado_por_id,
        eliminado_observacion=c.eliminado_observacion,
        created_at=c.created_at,
        updated_at=c.updated_at,
        archivos=[_to_archivo_response(a) for a in c.archivos],
        otrosies=[_to_otrosi_response(o) for o in c.otrosies],
    )


def _umbral_acta():
    return settings.liquidacion_acta_umbral_cop


def _to_list_item(c) -> ContratoListItem:
    return ContratoListItem(
        id=c.id,
        codigo=c.codigo,
        tipo_codigo=c.tipo_codigo,
        solicitud_gestion_id=c.solicitud_gestion_id,
        solicitud_gestion_codigo=c.solicitud_gestion_codigo or "",
        creado_por_username=c.creado_por_username,
        proveedor_contratista=c.proveedor_contratista,
        nit_proveedor=c.nit_proveedor,
        proveedor_email=getattr(c, "proveedor_email", "") or "",
        descripcion_servicio=c.descripcion_servicio,
        valor=c.valor,
        moneda=c.moneda,
        plazo_cantidad=c.plazo_cantidad,
        plazo_unidad=c.plazo_unidad,
        renovacion_automatica=c.renovacion_automatica,
        requiere_poliza=c.requiere_poliza,
        tipo_precio=c.tipo_precio,
        forma_pago=c.forma_pago or "",
        centro_costos=c.centro_costos or "",
        supervisor_id=c.supervisor_id,
        supervisor_username=c.supervisor_username or "",
        requiere_anticipo=bool(getattr(c, "requiere_anticipo", False)),
        anticipo_pagado=bool(getattr(c, "anticipo_pagado", False)),
        tiene_poliza=c.tiene_poliza(),
        tiene_borrador=c.tiene_borrador(),
        requiere_acta_liquidacion=c.requiere_acta_liquidacion(_umbral_acta()),
        tiene_informe_final=c.tiene_informe_final(),
        tiene_acta_liquidacion=c.tiene_acta_liquidacion(),
        pendiente_acta_liquidacion=c.esperando_acta_liquidacion(_umbral_acta()),
        cantidad_otrosies=c.cantidad_otrosies(),
        estado_aprobacion=c.estado_aprobacion,
        estado=c.estado,
        fecha_inicio=c.fecha_inicio,
        fecha_fin=c.fecha_fin,
        fecha_limite_elaboracion=c.fecha_limite_elaboracion_efectiva(),
        dias_para_elaborar=c.dias_para_elaborar(),
        alerta_elaboracion=_alerta_elaboracion(c),
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


def _actor_label(actor: User) -> str:
    if actor.is_juridica():
        return "Jurídica"
    if actor.is_compras():
        return "Compras"
    if actor.is_admin():
        return "Admin"
    return actor.username or "Alguien"


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
    proveedor_email: str = Form(""),
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
    tipo_precio: TipoPrecio = Form(TipoPrecio.MAS_IVA),
    forma_pago: str = Form(...),
    centro_costos: str = Form(..., description="Centro de costos del proyecto."),
    supervisor_id: Optional[int] = Form(None, description="Usuario supervisor encargado."),
    correo_lider_proceso: str = Form(...),
    correo_gerencia: str = Form(...),
    camara_comercio: UploadFile = File(..., description="PDF/Imagen — obligatorio"),
    cotizacion: Optional[UploadFile] = File(
        None, description="PDF/Imagen — obligatorio, o se copia la cotización elegida de la SRV"
    ),
    cedula_rep_legal: UploadFile = File(..., description="PDF/Imagen — obligatorio"),
    archivo_opcional: Optional[UploadFile] = File(None, description="Cualquier archivo"),
    solicitud_gestion_id: Optional[int] = Form(None),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> ContratoResponse:
    try:
        valor_decimal = Decimal(valor)
    except (InvalidOperation, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El valor del contrato no es un número válido.",
        )
    if (current.is_compras() or current.is_juridica()) and (
        fecha_inicio is not None
        or fecha_fin is not None
        or fecha_proxima_notificacion is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Las fechas de vigencia y notificación se asignan durante "
                "la formalización del contrato."
            ),
        )

    archivos: list[ArchivoEntrada] = []
    for upload, tipo, requerido in [
        (camara_comercio, TipoArchivo.CAMARA_COMERCIO, True),
        (cotizacion, TipoArchivo.COTIZACION, False),
        (cedula_rep_legal, TipoArchivo.CEDULA_REP_LEGAL, True),
        (archivo_opcional, TipoArchivo.OPCIONAL, False),
    ]:
        entrada = _validate_and_read(upload, tipo, requerido)
        if entrada is not None:
            archivos.append(entrada)

    try:
        contrato = RadicarSolicitud(contratos, storage, solicitudes).execute(
            actor=current,
            proveedor_contratista=proveedor_contratista,
            nit_proveedor=nit_proveedor,
            proveedor_email=proveedor_email,
            descripcion_servicio=descripcion_servicio,
            obligaciones_colbeef=obligaciones_colbeef,
            obligaciones_proveedor=obligaciones_proveedor,
            valor=valor_decimal,
            moneda=moneda,
            plazo_cantidad=plazo_cantidad,
            plazo_unidad=plazo_unidad,
            renovacion_automatica=renovacion_automatica,
            condiciones_recibido_satisfactorio=condiciones_recibido_satisfactorio,
            requiere_poliza=False,
            tipo_precio=tipo_precio,
            forma_pago=forma_pago,
            centro_costos=centro_costos,
            supervisor_id=supervisor_id,
            correo_lider_proceso=settings.APROBACION_DIEGO_SERRANO_EMAIL.strip(),
            correo_gerencia=correo_aprobacion_gerencia(valor_decimal, moneda)[0],
            tipo_codigo=tipo_codigo,
            archivos=archivos,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            fecha_proxima_notificacion=fecha_proxima_notificacion,
            solicitud_gestion_id=solicitud_gestion_id,
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except MissingRequiredFileError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # La aprobación Líder→Gerencia ya se hizo en la Solicitud de Servicio:
    # el contrato nace aprobado y se notifica directamente a Jurídica.
    background_tasks.add_task(_notificar_juridica_aprobado, contrato, notifier)

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


def _to_solicitud_info_response(s, contrato=None) -> SolicitudInformacionResponse:
    return SolicitudInformacionResponse(
        id=s.id,
        contrato_id=s.contrato_id,
        contrato_codigo=(contrato.codigo if contrato else None),
        proveedor_contratista=(contrato.proveedor_contratista if contrato else None),
        solicitado_por_id=s.solicitado_por_id,
        solicitado_por_username=s.solicitado_por_username or "",
        mensaje=s.mensaje,
        fecha_limite_respuesta=s.fecha_limite_respuesta,
        dias_para_responder=s.dias_para_responder(),
        vencida=s.vencida(),
        estado=s.estado,
        respuesta=s.respuesta or "",
        respondido_por_id=s.respondido_por_id,
        respondido_por_username=s.respondido_por_username or "",
        respondido_at=s.respondido_at,
        created_at=s.created_at,
        archivos=[
            ArchivoResponse(
                id=a.id,
                tipo=a.tipo,
                nombre_original=a.nombre_original,
                mime_type=a.mime_type,
                tamano_bytes=a.tamano_bytes,
                subido_por_id=a.subido_por_id,
                created_at=a.created_at,
            )
            for a in s.archivos
        ],
    )


@router.get(
    "/solicitudes-informacion/pendientes",
    response_model=list[SolicitudInformacionResponse],
)
def list_solicitudes_informacion_pendientes(
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> list[SolicitudInformacionResponse]:
    """Avisos in-app: solicitudes de información pendientes.

    - Compras: las de los contratos que radicó.
    - Jurídica/Admin: todas las pendientes.
    """
    pendientes = contratos.list_solicitudes_informacion_pendientes()
    resultado = []
    for contrato, solicitud in pendientes:
        if current.is_compras() and contrato.creado_por_id != current.id:
            continue
        if not (current.is_admin() or current.is_juridica() or current.is_compras()):
            continue
        resultado.append(_to_solicitud_info_response(solicitud, contrato))
    return resultado


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
        solicitud_gestion_id=contrato.solicitud_gestion_id,
        solicitud_gestion_codigo=contrato.solicitud_gestion_codigo or "",
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
                    <h1>JURICOM</h1>
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


@router.get("/minutas/plantillas")
def listar_plantillas_minuta(
    current: User = Depends(get_current_user),
) -> list[dict]:
    if not (current.is_juridica() or current.is_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo Jurídica puede generar minutas.",
        )
    return [{"clave": k, "nombre": v["nombre"]} for k, v in PLANTILLAS.items()]


@router.get("/{contrato_id}/minuta/{plantilla}")
def generar_minuta_contrato(
    contrato_id: int,
    plantilla: str,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> Response:
    if not (current.is_juridica() or current.is_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo Jurídica puede generar minutas.",
        )
    if plantilla not in PLANTILLAS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla de minuta desconocida.",
        )
    contrato = contratos.get_by_id(contrato_id)
    if contrato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe el contrato {contrato_id}.",
        )
    datos = generar_minuta(plantilla, contrato)
    codigo = (getattr(contrato, "codigo", "") or str(contrato_id)).replace("/", "-")
    nombre = f"Minuta {PLANTILLAS[plantilla]['nombre']} {codigo}.docx"
    return Response(
        content=datos,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{contrato_id}/aprobar/{paso}", response_class=HTMLResponse)
def aprobar_por_correo(
    contrato_id: int,
    paso: str,
    token: str = Query(...),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> HTMLResponse:
    if paso not in ("lider", "gerencia") or not _validar_token(contrato_id, paso, token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token inválido.")

    try:
        caso = AprobarContrato(contratos)
        if paso == "lider":
            contrato = caso.aprobar_lider(contrato_id)
            _notificar_gerencia_aprobacion(contrato, notifier)
            evento = f"El líder aprobó el contrato {contrato.codigo}."
            mensaje = (
                "Aprobación del líder registrada. "
                "Ahora se notificó a Gerencia para la aprobación final."
            )
        else:
            contrato = caso.aprobar_gerencia(contrato_id)
            _notificar_juridica_aprobado(contrato, notifier)
            _notificar_lider_contrato_en_juridica(contrato, notifier)
            evento = f"Gerencia aprobó el contrato {contrato.codigo}."
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

    registrar_evento_contrato_en_srv(solicitudes, contrato, None, evento)

    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Contrato aprobado</title></head>
        <body style="font-family: Arial, sans-serif; padding: 32px;">
            <h1 style="color:#1f4e8a;">JURICOM</h1>
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
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
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

    quien = "El líder" if paso == "lider" else "Gerencia"
    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        None,
        f"{quien} rechazó la solicitud del contrato {contrato.codigo}.",
    )

    return HTMLResponse(
        f"""<!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><title>Solicitud rechazada</title></head>
        <body style="font-family: Arial, sans-serif; padding: 32px;">
            <h1 style="color:#1f4e8a;">JURICOM</h1>
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
            <h1 style="color:#1f4e8a;">JURICOM</h1>
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
            asunto=f"[JURICOM] Aprobación Gerencia — {contrato.codigo}",
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
            asunto=f"[JURICOM] Contrato pendiente por revisar — {contrato.codigo}",
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
            asunto=f"[JURICOM] Contrato en Jurídica — {contrato.codigo}",
            destinatarios=[contrato.correo_lider_proceso],
            cuerpo_html=render_seguimiento_lider_juridica_html(contrato, token),
            cuerpo_texto=render_seguimiento_lider_juridica_texto(contrato, token),
        )
    )


@router.put("/{contrato_id}/estado", response_model=ContratoResponse)
def cambiar_estado(
    contrato_id: int,
    payload: CambiarEstadoRequest,
    background_tasks: BackgroundTasks,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    previo = contratos.get_by_id(contrato_id)
    estado_anterior = previo.estado if previo else None
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
    observacion = (payload.observacion or "").strip()
    if estado_anterior != contrato.estado:
        comentario = (
            f"Jurídica actualizó el estado de {contrato.codigo}: "
            f"{etiqueta_estado_contrato(estado_anterior)} → "
            f"{etiqueta_estado_contrato(contrato.estado)}"
        )
        if observacion:
            comentario = f"{comentario} — Observación: {observacion}"
        registrar_evento_contrato_en_srv(
            solicitudes,
            contrato,
            current.id,
            comentario,
            etapa=etapa_historial_contrato(contrato.estado),
        )
        if observacion:
            registrar_observacion_contrato_en_srv(
                solicitudes, contrato, current, observacion
            )
        background_tasks.add_task(
            _notificar_cambio_estado_supervisor,
            contrato,
            estado_anterior,
            notifier,
            users,
        )
    return _to_contrato_response(contrato)


def _guardar_evidencia_srv(uploads, storage: FileStorage, actor_id):
    """Guarda adjuntos de evidencia y devuelve entidades SolicitudGestionArchivo."""
    from app.domain.entities.solicitud_gestion import SolicitudGestionArchivo

    entidades = []
    for upload in uploads or []:
        if not upload or not upload.filename:
            continue
        contenido = upload.file.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        stored = storage.save(
            contenido=contenido,
            nombre_original=upload.filename,
            mime_type=upload.content_type or "application/octet-stream",
            subcarpeta="solicitudes/anticipo",
        )
        entidades.append(
            SolicitudGestionArchivo(
                nombre_original=stored.nombre_original,
                ruta_almacenamiento=stored.ruta,
                mime_type=stored.mime_type,
                tamano_bytes=stored.tamano_bytes,
                categoria="observacion",
                subido_por_id=actor_id,
            )
        )
    return entidades


def _registrar_traza_anticipo(
    solicitudes,
    storage,
    contrato,
    actor,
    comentario_flujo,
    observacion,
    uploads,
    contexto,
    observacion_html: str = "",
) -> None:
    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        actor.id,
        comentario_flujo,
        etapa=etapa_historial_contrato(contrato.estado),
    )
    archivos = _guardar_evidencia_srv(uploads, storage, actor.id)
    texto = (observacion or "").strip()
    html = (observacion_html or "").strip()
    if texto or html or archivos:
        registrar_observacion_contrato_en_srv(
            solicitudes,
            contrato,
            actor,
            texto,
            contexto=contexto,
            archivos=archivos,
            contenido_html=html,
            storage=storage,
        )


def _emails_por_rol(users: UserRepository, rol) -> list[str]:
    correos = []
    for u in users.list_all():
        if getattr(u, "role", None) == rol and getattr(u, "email", "") and u.is_active:
            correos.append(u.email)
    return list(dict.fromkeys(correos))


def _notificar_anticipo_rol(contrato, notifier, users, rol, titulo, cuerpo) -> None:
    from app.domain.value_objects.roles import Role

    if not notifier.disponible:
        return
    destinatarios = _emails_por_rol(users, rol)
    if not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    html = f"<p>{cuerpo}</p><p>Contrato <b>{codigo}</b> ({proveedor}).</p>"
    texto = f"{cuerpo} Contrato {contrato.codigo} ({contrato.proveedor_contratista or ''})."
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] {titulo} — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


def _notificar_anticipo_pagado(contrato, notifier, users: UserRepository) -> None:
    """Tras el pago, avisa a Jurídica, Compras y al supervisor."""
    if not notifier.disponible:
        return
    destinatarios = list(settings.juridica_emails_list) + list(settings.compras_emails_list)
    if contrato.supervisor_id:
        supervisor = users.get_by_id(contrato.supervisor_id)
        if supervisor and supervisor.email:
            destinatarios.append(supervisor.email)
    destinatarios = list(dict.fromkeys(e for e in destinatarios if e))
    if not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    html = (
        f"<p>Tesorería confirmó el <b>pago del anticipo</b> del contrato "
        f"<b>{codigo}</b> ({proveedor}).</p>"
        f"<p>El contrato quedó en estado <b>Anticipo pagado</b>. "
        f"Jurídica puede continuar el flujo y activarlo cuando corresponda.</p>"
    )
    texto = (
        f"Tesorería confirmó el pago del anticipo del contrato {contrato.codigo} "
        f"({contrato.proveedor_contratista or ''}). El contrato quedó en 'Anticipo "
        f"pagado'; Jurídica puede continuar y activarlo."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Anticipo pagado — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


@router.post("/{contrato_id}/anticipo/enviar-contabilidad", response_model=ContratoResponse)
def anticipo_enviar_contabilidad(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    observacion: str = Form(""),
    observacion_html: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    from app.domain.value_objects.roles import Role

    try:
        contrato = EnviarAnticipoContabilidad(contratos).execute(current, contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    _registrar_traza_anticipo(
        solicitudes,
        storage,
        contrato,
        current,
        f"Jurídica envió el anticipo de {contrato.codigo} a Contabilidad",
        observacion,
        adjuntos,
        contexto="juridica",
        observacion_html=observacion_html,
    )
    background_tasks.add_task(
        _notificar_anticipo_rol,
        contrato,
        notifier,
        users,
        Role.CONTABILIDAD,
        "Anticipo recibido para gestión",
        "Jurídica envió un anticipo para que lo gestiones.",
    )
    background_tasks.add_task(
        _notificar_estado_supervisor,
        contrato,
        notifier,
        users,
        titulo="Anticipo en Contabilidad",
        mensaje="Tu contrato pasó a Contabilidad para gestionar el anticipo.",
    )
    return _to_contrato_response(contrato)


@router.post("/{contrato_id}/anticipo/gestionar", response_model=ContratoResponse)
def anticipo_gestionar_contabilidad(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    observacion: str = Form(""),
    observacion_html: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    from app.domain.value_objects.roles import Role

    try:
        contrato = GestionarAnticipoContabilidad(contratos).execute(current, contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    _registrar_traza_anticipo(
        solicitudes,
        storage,
        contrato,
        current,
        f"Contabilidad gestionó el anticipo de {contrato.codigo} y lo envió a Tesorería",
        observacion,
        adjuntos,
        contexto="contabilidad",
        observacion_html=observacion_html,
    )
    background_tasks.add_task(
        _notificar_anticipo_rol,
        contrato,
        notifier,
        users,
        Role.TESORERIA,
        "Anticipo listo para pago",
        "Contabilidad gestionó un anticipo y queda pendiente tu revisión y pago.",
    )
    background_tasks.add_task(
        _notificar_estado_supervisor,
        contrato,
        notifier,
        users,
        titulo="Anticipo en Tesorería",
        mensaje="El anticipo de tu contrato pasó a Tesorería para el pago.",
    )
    return _to_contrato_response(contrato)


@router.post("/{contrato_id}/anticipo/confirmar-pago", response_model=ContratoResponse)
def anticipo_confirmar_pago(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    observacion: str = Form(""),
    observacion_html: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    try:
        contrato = ConfirmarPagoTesoreria(contratos).execute(current, contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    _registrar_traza_anticipo(
        solicitudes,
        storage,
        contrato,
        current,
        f"Tesorería confirmó el pago del anticipo de {contrato.codigo}; el contrato quedó en 'Anticipo pagado' y se avisó a Jurídica",
        observacion,
        adjuntos,
        contexto="tesoreria",
        observacion_html=observacion_html,
    )
    background_tasks.add_task(_notificar_anticipo_pagado, contrato, notifier, users)
    return _to_contrato_response(contrato)


def _notificar_contrato_completado(
    contrato, notifier: EmailNotifier, users: UserRepository
) -> None:
    """Tras el pago final de Tesorería, avisa a Jurídica, Compras y al supervisor."""
    if not notifier.disponible:
        return
    destinatarios = list(settings.juridica_emails_list) + list(settings.compras_emails_list)
    if contrato.supervisor_id:
        supervisor = users.get_by_id(contrato.supervisor_id)
        if supervisor and supervisor.email:
            destinatarios.append(supervisor.email)
    destinatarios = list(dict.fromkeys(e for e in destinatarios if e))
    if not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    html = (
        f"<p>Tesorería confirmó el <b>pago final</b> del contrato "
        f"<b>{codigo}</b> ({proveedor}).</p>"
        f"<p>El contrato quedó <b>Completado</b>: finaliza el proceso de cierre en "
        f"Contabilidad y Tesorería. Toda la trazabilidad y los archivos quedan "
        f"disponibles en la solicitud.</p>"
    )
    texto = (
        f"Tesorería confirmó el pago final del contrato {contrato.codigo} "
        f"({contrato.proveedor_contratista or ''}). El contrato quedó 'Completado'."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Contrato completado — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


@router.post("/{contrato_id}/cierre/gestionar", response_model=ContratoResponse)
def cierre_gestionar_contabilidad(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    observacion: str = Form(""),
    observacion_html: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    from app.domain.value_objects.roles import Role

    try:
        contrato = GestionarCierreContabilidad(contratos).execute(current, contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    _registrar_traza_anticipo(
        solicitudes,
        storage,
        contrato,
        current,
        f"Contabilidad gestionó el cierre de {contrato.codigo} y lo envió a Tesorería para el pago final",
        observacion,
        adjuntos,
        contexto="contabilidad",
        observacion_html=observacion_html,
    )
    background_tasks.add_task(
        _notificar_anticipo_rol,
        contrato,
        notifier,
        users,
        Role.TESORERIA,
        "Cierre listo para pago final",
        "Contabilidad gestionó el cierre de un contrato y queda pendiente tu pago final.",
    )
    background_tasks.add_task(
        _notificar_estado_supervisor,
        contrato,
        notifier,
        users,
        titulo="Cierre en Tesorería",
        mensaje="El cierre de tu contrato pasó a Tesorería para el pago final.",
    )
    return _to_contrato_response(contrato)


@router.post("/{contrato_id}/cierre/confirmar", response_model=ContratoResponse)
def cierre_confirmar_tesoreria(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    observacion: str = Form(""),
    observacion_html: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    try:
        contrato = ConfirmarCierreTesoreria(contratos).execute(current, contrato_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        current.id,
        f"Tesorería confirmó el pago final de {contrato.codigo}; el contrato quedó 'Completado'",
        etapa=EstadoSolicitudGestion.CONTRATO_COMPLETADO,
        nuevo_estado=EstadoSolicitudGestion.CONTRATO_COMPLETADO,
    )
    archivos = _guardar_evidencia_srv(adjuntos, storage, current.id)
    texto = (observacion or "").strip()
    html = (observacion_html or "").strip()
    if texto or html or archivos:
        registrar_observacion_contrato_en_srv(
            solicitudes,
            contrato,
            current,
            texto,
            contexto="tesoreria",
            archivos=archivos,
            contenido_html=html,
            storage=storage,
        )
    background_tasks.add_task(_notificar_contrato_completado, contrato, notifier, users)
    return _to_contrato_response(contrato)


def _leer_upload_finalizacion(
    upload: Optional[UploadFile], tipo: TipoArchivo
) -> Optional[ArchivoFinalizacion]:
    if upload is None or not upload.filename:
        return None
    contenido = upload.file.read()
    if len(contenido) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    return ArchivoFinalizacion(
        tipo=tipo,
        nombre_original=upload.filename,
        mime_type=upload.content_type or "application/octet-stream",
        contenido=contenido,
    )


@router.post("/{contrato_id}/finalizar", response_model=ContratoResponse)
def finalizar_contrato(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    informe_final: UploadFile = File(..., description="Informe final (obligatorio)."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    informe = _leer_upload_finalizacion(informe_final, TipoArchivo.INFORME_FINAL)
    try:
        contrato = FinalizarContratoCompras(
            contratos, storage, umbral_acta=_umbral_acta()
        ).execute(
            actor=current,
            contrato_id=contrato_id,
            informe_final=informe,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    from app.domain.value_objects.roles import Role

    if contrato.estado == EstadoContrato.CIERRE_CONTABILIDAD:
        registrar_evento_contrato_en_srv(
            solicitudes,
            contrato,
            current.id,
            f"Supervisor entregó el informe final de {contrato.codigo}; "
            f"el contrato pasó a Cierre en contabilidad",
            etapa=EstadoSolicitudGestion.CIERRE_CONTABILIDAD,
        )
        background_tasks.add_task(
            _notificar_anticipo_rol,
            contrato,
            notifier,
            users,
            Role.CONTABILIDAD,
            "Cierre de contrato para gestión",
            "El supervisor finalizó un contrato. Gestiona el cierre y envíalo a Tesorería.",
        )
        background_tasks.add_task(
            _notificar_estado_supervisor,
            contrato,
            notifier,
            users,
            titulo="Cierre en Contabilidad",
            mensaje="Tu contrato pasó a Contabilidad para gestionar el cierre y el pago final.",
        )
    else:
        # Contrato > umbral: el informe quedó entregado; Jurídica debe elaborar el acta.
        registrar_evento_contrato_en_srv(
            solicitudes,
            contrato,
            current.id,
            f"Supervisor entregó el informe final de {contrato.codigo}; "
            f"pendiente el acta de liquidación de Jurídica",
        )
        # Adjunta el informe final para que Jurídica lo tenga a la mano al elaborar el acta.
        adjunto_informe = EmailAttachment(
            nombre=informe.nombre_original,
            contenido=informe.contenido,
            mime_type=informe.mime_type,
        )
        background_tasks.add_task(
            _notificar_pendiente_acta_liquidacion, contrato, notifier, adjunto_informe
        )
    return _to_contrato_response(contrato)


@router.post("/{contrato_id}/acta-liquidacion", response_model=ContratoResponse)
def cargar_acta_liquidacion(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    acta_liquidacion: UploadFile = File(..., description="Acta de liquidación (obligatoria)."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> ContratoResponse:
    acta = _leer_upload_finalizacion(acta_liquidacion, TipoArchivo.ACTA_LIQUIDACION)
    try:
        contrato = CargarActaLiquidacion(
            contratos, storage, umbral_acta=_umbral_acta()
        ).execute(
            actor=current,
            contrato_id=contrato_id,
            acta_liquidacion=acta,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    from app.domain.value_objects.roles import Role

    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        current.id,
        f"Jurídica cargó el acta de liquidación de {contrato.codigo}; "
        f"el contrato pasó a Cierre en contabilidad",
        etapa=EstadoSolicitudGestion.CIERRE_CONTABILIDAD,
    )
    background_tasks.add_task(
        _notificar_anticipo_rol,
        contrato,
        notifier,
        users,
        Role.CONTABILIDAD,
        "Cierre de contrato para gestión",
        "Jurídica cargó el acta de liquidación. Gestiona el cierre y envíalo a Tesorería.",
    )
    # Devuelve el acta de liquidación al supervisor por correo (adjunta).
    adjunto_acta = EmailAttachment(
        nombre=acta.nombre_original,
        contenido=acta.contenido,
        mime_type=acta.mime_type,
    )
    background_tasks.add_task(
        _notificar_acta_a_supervisor, contrato, notifier, users, adjunto_acta
    )
    return _to_contrato_response(contrato)


def _notificar_pendiente_acta_liquidacion(
    contrato, notifier: EmailNotifier, adjunto: EmailAttachment | None = None
) -> None:
    """Avisa a Jurídica que el supervisor entregó el informe final y falta el acta.

    Adjunta el informe final (si se recibe) para que Jurídica elabore el acta.
    """
    if not notifier.disponible:
        return
    destinatarios = list(dict.fromkeys(e for e in settings.juridica_emails_list if e))
    if not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    supervisor = escape(contrato.supervisor_username or "el supervisor")
    url = f"{settings.public_url}/app/juridica/editar-contrato.html"
    if contrato.codigo:
        url = f"{url}?codigo={contrato.codigo}"
    adjunto_nota = (
        "<p>Adjuntamos el informe final entregado por el supervisor.</p>" if adjunto else ""
    )
    html = (
        f"<p><b>{supervisor}</b> entregó el <b>informe final</b> del contrato "
        f"<b>{codigo}</b> ({proveedor}), cuyo valor supera el umbral para acta de "
        f"liquidación.</p>"
        f"{adjunto_nota}"
        f"<p>Por favor elabora y carga el <b>acta de liquidación</b> para finalizar "
        f"el contrato.</p>"
        f'<p><a href="{escape(url)}">Abrir el contrato</a></p>'
    )
    texto = (
        f"{contrato.supervisor_username or 'El supervisor'} entregó el informe final "
        f"del contrato {contrato.codigo} ({contrato.proveedor_contratista or ''}). "
        f"Jurídica debe elaborar y cargar el acta de liquidación para finalizarlo. "
        f"{url}"
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Falta acta de liquidación — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
            adjuntos=[adjunto] if adjunto else [],
        )
    )


def _notificar_acta_a_supervisor(
    contrato, notifier: EmailNotifier, users: UserRepository, adjunto: EmailAttachment | None = None
) -> None:
    """Envía el acta de liquidación de vuelta al supervisor del contrato (adjunta)."""
    if not notifier.disponible or not contrato.supervisor_id:
        return
    supervisor = users.get_by_id(contrato.supervisor_id)
    if not supervisor or not supervisor.email:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    adjunto_nota = "<p>Adjuntamos el acta de liquidación.</p>" if adjunto else ""
    html = (
        f"<p>Jurídica elaboró el <b>acta de liquidación</b> del contrato "
        f"<b>{codigo}</b> ({proveedor}).</p>"
        f"{adjunto_nota}"
        f"<p>El contrato continúa con el cierre administrativo (Contabilidad → Tesorería).</p>"
    )
    texto = (
        f"Jurídica elaboró el acta de liquidación del contrato {contrato.codigo} "
        f"({contrato.proveedor_contratista or ''}). Se adjunta el acta."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Acta de liquidación — {contrato.codigo}",
            destinatarios=[supervisor.email],
            cuerpo_html=html,
            cuerpo_texto=texto,
            adjuntos=[adjunto] if adjunto else [],
        )
    )


def _notificar_contrato_finalizado(
    contrato, notifier: EmailNotifier, users: UserRepository
) -> None:
    """Avisa a Compras, Jurídica y al supervisor que la operación quedó finalizada."""
    if not notifier.disponible:
        return
    destinatarios = list(settings.compras_emails_list) + list(settings.juridica_emails_list)
    if contrato.supervisor_id:
        supervisor = users.get_by_id(contrato.supervisor_id)
        if supervisor and supervisor.email:
            destinatarios.append(supervisor.email)
    destinatarios = list(dict.fromkeys(e for e in destinatarios if e))
    if not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    html = (
        f"<p>El contrato/servicio <b>{codigo}</b> ({proveedor}) fue "
        f"<b>finalizado</b> por el supervisor.</p>"
        f"<p>El informe final y el acta de liquidación quedaron cargados. "
        f"La operación del servicio queda <b>completada</b> y cerrada.</p>"
    )
    texto = (
        f"El contrato/servicio {contrato.codigo} ({contrato.proveedor_contratista or ''}) "
        f"fue finalizado por el supervisor. Informe final y acta de liquidación cargados. "
        f"Operación completada y cerrada."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Contrato finalizado — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


def _notificar_cambio_estado_supervisor(
    contrato, estado_anterior, notifier: EmailNotifier, users: UserRepository
) -> None:
    """Avisa al supervisor que Jurídica actualizó el estado del contrato."""
    if not contrato or not contrato.supervisor_id:
        return
    supervisor = users.get_by_id(contrato.supervisor_id)
    if not notifier.disponible or not supervisor or not supervisor.email:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    anterior = escape(etiqueta_estado_contrato(estado_anterior))
    actual = escape(etiqueta_estado_contrato(contrato.estado))
    url = "/app/compras/finalizar-contrato.html"
    if contrato.codigo:
        url = f"/app/compras/finalizar-contrato.html?codigo={contrato.codigo}"
    html = (
        f"<p>Jurídica actualizó el estado del contrato <b>{codigo}</b> "
        f"({escape(contrato.proveedor_contratista or '')}).</p>"
        f"<p><b>Estado anterior:</b> {anterior}<br>"
        f"<b>Estado actual:</b> {actual}</p>"
        f"<p>Revisa el contrato y la conversación con Jurídica en "
        f"<a href=\"{escape(url)}\">Finalizar contrato</a>.</p>"
    )
    texto = (
        f"Jurídica actualizó el estado del contrato {contrato.codigo}: "
        f"{etiqueta_estado_contrato(estado_anterior)} → "
        f"{etiqueta_estado_contrato(contrato.estado)}."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Estado actualizado — {contrato.codigo}",
            destinatarios=[supervisor.email],
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


def _notificar_estado_supervisor(
    contrato,
    notifier: EmailNotifier,
    users: UserRepository,
    *,
    titulo: str,
    mensaje: str,
) -> None:
    """Aviso simple al supervisor de que su contrato entró a una etapa
    (p. ej. «tu contrato está en Contabilidad»)."""
    if not contrato or not contrato.supervisor_id or not notifier.disponible:
        return
    supervisor = users.get_by_id(contrato.supervisor_id)
    if not supervisor or not supervisor.email:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    proveedor = escape(contrato.proveedor_contratista or "")
    url = "/app/compras/finalizar-contrato.html"
    if contrato.codigo:
        url = f"/app/compras/finalizar-contrato.html?codigo={contrato.codigo}"
    html = (
        f"<p>{escape(mensaje)}</p>"
        f"<p><b>Contrato:</b> {codigo} ({proveedor})</p>"
        f"<p>Puedes seguir la trazabilidad en "
        f"<a href=\"{escape(url)}\">Finalizar contrato</a>.</p>"
    )
    texto = (
        f"{mensaje} Contrato {contrato.codigo} "
        f"({contrato.proveedor_contratista or ''})."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] {titulo} — {contrato.codigo}",
            destinatarios=[supervisor.email],
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


def _notificar_solicitud_informacion(
    contrato, solicitud, notifier: EmailNotifier, users: UserRepository
) -> None:
    """Avisa al supervisor asignado que Jurídica pidió información faltante."""
    destinatarios: list[str] = []
    if contrato.supervisor_id:
        supervisor = users.get_by_id(contrato.supervisor_id)
        if supervisor and supervisor.email:
            destinatarios = [supervisor.email]
    if not notifier.disponible or not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    limite = solicitud.fecha_limite_respuesta.isoformat() if solicitud.fecha_limite_respuesta else "—"
    mensaje = escape(solicitud.mensaje)
    html = (
        f"<p>Jurídica solicitó información faltante para el contrato <b>{codigo}</b> "
        f"({escape(contrato.proveedor_contratista)}).</p>"
        f"<p><b>Información solicitada:</b><br>{mensaje}</p>"
        f"<p>Tienes hasta el <b>{limite}</b> (2 días hábiles) para responder desde "
        f"“Finalizar contrato” o desde el detalle de tu solicitud de servicios.</p>"
    )
    texto = (
        f"Jurídica solicitó información para el contrato {contrato.codigo}. "
        f"Información: {solicitud.mensaje}. Fecha límite: {limite}."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Información faltante — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


def _notificar_respuesta_informacion(contrato, solicitud, notifier: EmailNotifier) -> None:
    """Avisa a Jurídica que Compras respondió con la información."""
    destinatarios = settings.juridica_emails_list
    if not notifier.disponible or not destinatarios:
        return
    codigo = escape(contrato.codigo or f"#{contrato.id}")
    respuesta = escape(solicitud.respuesta)
    html = (
        f"<p>El supervisor respondió la información faltante del contrato <b>{codigo}</b> "
        f"({escape(contrato.proveedor_contratista)}).</p>"
        f"<p><b>Respuesta:</b><br>{respuesta}</p>"
        f"<p>Revisa el contrato en Edición de contratos.</p>"
    )
    texto = (
        f"El supervisor respondió el contrato {contrato.codigo}. Respuesta: {solicitud.respuesta}."
    )
    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Información recibida — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=html,
            cuerpo_texto=texto,
        )
    )


@router.post(
    "/{contrato_id}/solicitudes-informacion",
    response_model=SolicitudInformacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def solicitar_informacion(
    contrato_id: int,
    background_tasks: BackgroundTasks,
    mensaje: str = Form(..., description="Qué información falta."),
    archivos: list[UploadFile] = File(default=[], description="Fotos u otros adjuntos (opcional)."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
    users: UserRepository = Depends(get_user_repository),
) -> SolicitudInformacionResponse:
    entradas: list[ArchivoSolicitudInfo] = []
    for upload in archivos or []:
        if upload is None or not upload.filename:
            continue
        contenido = upload.file.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        entradas.append(
            ArchivoSolicitudInfo(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud = SolicitarInformacion(contratos, storage).execute(
            actor=current,
            contrato_id=contrato_id,
            mensaje=mensaje,
            archivos=entradas,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    contrato = contratos.get_by_id(contrato_id)
    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        current.id,
        (
            f"Jurídica solicitó información al supervisor ({contrato.codigo}): "
            f"{solicitud.mensaje}"
        ),
        etapa=EstadoSolicitudGestion.SOLICITANDO_INFO,
    )
    background_tasks.add_task(
        _notificar_solicitud_informacion, contrato, solicitud, notifier, users
    )
    return _to_solicitud_info_response(solicitud, contrato)


@router.get(
    "/{contrato_id}/solicitudes-informacion",
    response_model=list[SolicitudInformacionResponse],
)
def list_solicitudes_informacion(
    contrato_id: int,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> list[SolicitudInformacionResponse]:
    contrato = contratos.get_by_id(contrato_id)
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe el contrato.")
    if current.is_solicitante() and contrato.supervisor_id != current.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo puedes ver solicitudes de contratos donde eres supervisor.",
        )
    items = contratos.list_solicitudes_informacion_by_contrato(contrato_id)
    return [_to_solicitud_info_response(s, contrato) for s in items]


@router.post(
    "/{contrato_id}/solicitudes-informacion/{solicitud_id}/responder",
    response_model=SolicitudInformacionResponse,
)
def responder_informacion(
    contrato_id: int,
    solicitud_id: int,
    background_tasks: BackgroundTasks,
    respuesta: str = Form(..., description="Información solicitada."),
    archivos: list[UploadFile] = File(default=[], description="Adjuntos (opcional)."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> SolicitudInformacionResponse:
    entradas: list[ArchivoRespuesta] = []
    for upload in archivos or []:
        if upload is None or not upload.filename:
            continue
        contenido = upload.file.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        entradas.append(
            ArchivoRespuesta(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud = ResponderInformacion(contratos, storage).execute(
            actor=current,
            contrato_id=contrato_id,
            solicitud_id=solicitud_id,
            respuesta=respuesta,
            archivos=entradas,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    contrato = contratos.get_by_id(contrato_id)
    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        current.id,
        (
            f"Supervisor respondió a Jurídica ({contrato.codigo}): "
            f"{solicitud.respuesta}"
        ),
        etapa=EstadoSolicitudGestion.INFO_RECIBIDA,
    )
    background_tasks.add_task(
        _notificar_respuesta_informacion, contrato, solicitud, notifier
    )
    return _to_solicitud_info_response(solicitud, contrato)


@router.put("/{contrato_id}", response_model=ContratoResponse)
def editar_contrato(
    contrato_id: int,
    payload: EditarContratoRequest,
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> ContratoResponse:
    try:
        contrato = EditarContrato(contratos).execute(
            actor=current,
            contrato_id=contrato_id,
            proveedor_contratista=payload.proveedor_contratista,
            nit_proveedor=payload.nit_proveedor,
            proveedor_email=payload.proveedor_email,
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
            tipo_precio=payload.tipo_precio,
            forma_pago=payload.forma_pago,
            centro_costos=payload.centro_costos,
            supervisor_id=payload.supervisor_id,
            fecha_inicio=payload.fecha_inicio,
            fecha_fin=payload.fecha_fin,
            fecha_proxima_notificacion=payload.fecha_proxima_notificacion,
            hora_proxima_notificacion=payload.hora_proxima_notificacion,
            fecha_limite_elaboracion=payload.fecha_limite_elaboracion,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    registrar_evento_contrato_en_srv(
        solicitudes,
        contrato,
        current.id,
        f"{_actor_label(current)} actualizó los datos del contrato {contrato.codigo}.",
    )
    return _to_contrato_response(contrato)


def _adjuntar_archivo_juridica(
    contrato_id: int,
    tipo: TipoArchivo,
    upload: UploadFile,
    current: User,
    contratos: ContratoRepository,
    storage: FileStorage,
    solicitudes: Optional[SolicitudGestionRepository] = None,
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
    if solicitudes is not None:
        contrato = contratos.get_by_id(contrato_id)
        doc = "la póliza" if tipo == TipoArchivo.POLIZA else "el contrato firmado (borrador)"
        registrar_evento_contrato_en_srv(
            solicitudes,
            contrato,
            current.id,
            f"{_actor_label(current)} cargó {doc} de {getattr(contrato, 'codigo', '')}.",
        )
    return _to_archivo_response(archivo)


@router.post("/{contrato_id}/poliza", response_model=ArchivoResponse)
def subir_poliza(
    contrato_id: int,
    archivo: UploadFile = File(..., description="PDF de la póliza."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> ArchivoResponse:
    return _adjuntar_archivo_juridica(
        contrato_id, TipoArchivo.POLIZA, archivo, current, contratos, storage, solicitudes
    )


@router.post("/{contrato_id}/borrador", response_model=ArchivoResponse)
def subir_borrador(
    contrato_id: int,
    archivo: UploadFile = File(..., description="PDF del contrato firmado (borrador)."),
    current: User = Depends(get_current_user),
    contratos: ContratoRepository = Depends(get_contrato_repository),
    storage: FileStorage = Depends(get_file_storage),
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> ArchivoResponse:
    return _adjuntar_archivo_juridica(
        contrato_id, TipoArchivo.BORRADOR_FIRMADO, archivo, current, contratos, storage, solicitudes
    )


@router.post("/{contrato_id}/otrosi", response_model=ContratoResponse)
def aplicar_otrosi(
    contrato_id: int,
    tipo: TipoOtrosi = Form(..., description="prorroga | adicion | prorroga_adicion"),
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
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
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

    registrar_evento_contrato_en_srv(
        solicitudes,
        resultado.contrato,
        current.id,
        f"{_actor_label(current)} solicitó un otrosí ({tipo.label}) para {resultado.contrato.codigo}.",
    )

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
            <h2>JURICOM</h2>
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
            <h2>JURICOM</h2>
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
    solicitudes: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
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
    registrar_evento_contrato_en_srv(
        solicitudes,
        final,
        current.id,
        f"{_actor_label(current)} finalizó un otrosí ({tipo.label}) de {getattr(final, 'codigo', '')}.",
    )
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

    if not (tipo.incluye_prorroga or tipo.incluye_adicion):
        raise ValueError("El otrosí debe incluir al menos una prórroga o una adición.")

    if tipo.incluye_prorroga:
        if not plazo_adicional_cantidad or plazo_adicional_cantidad <= 0:
            raise ValueError("Para una prórroga debes indicar plazo adicional mayor a 0.")
        otrosi.plazo_adicional_cantidad = plazo_adicional_cantidad
        otrosi.plazo_adicional_unidad = contrato.plazo_unidad
    if tipo.incluye_adicion:
        if valor_adicional is None or Decimal(valor_adicional) <= 0:
            raise ValueError("Para una adición debes indicar valor adicional mayor a 0.")
        otrosi.valor_adicional = Decimal(valor_adicional)


def _aplicar_cambios_otrosi_al_contrato(contrato, otrosi) -> None:
    if otrosi.plazo_adicional_cantidad is not None:
        contrato.plazo_cantidad += otrosi.plazo_adicional_cantidad
    if otrosi.valor_adicional is not None:
        contrato.valor = (contrato.valor or Decimal("0")) + Decimal(otrosi.valor_adicional)
    if otrosi.nueva_descripcion_servicio:
        contrato.descripcion_servicio = otrosi.nueva_descripcion_servicio


def _notificar_solicitud_otrosi(contrato, otrosi, current: User, notifier: EmailNotifier) -> None:
    email = (settings.APROBACION_DIEGO_SERRANO_EMAIL or "").strip()
    destinatarios = [email] if email else []
    if not notifier.disponible or not destinatarios:
        return
    from app.infrastructure.email.templates import (
        render_solicitud_otrosi_html,
        render_solicitud_otrosi_texto,
    )
    token = _otrosi_approval_token(contrato.id, otrosi.id, "lider")

    notifier.send(
        EmailMessage(
            asunto=f"[JURICOM] Solicitud de otrosí — {contrato.codigo}",
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
            asunto=f"[JURICOM] Aprobación Gerencia otrosí — {contrato.codigo}",
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
            asunto=f"[JURICOM] Otrosí pendiente Jurídica — {contrato.codigo}",
            destinatarios=destinatarios,
            cuerpo_html=render_otrosi_pendiente_juridica_html(contrato, otrosi),
            cuerpo_texto=render_otrosi_pendiente_juridica_texto(contrato, otrosi),
        )
    )
