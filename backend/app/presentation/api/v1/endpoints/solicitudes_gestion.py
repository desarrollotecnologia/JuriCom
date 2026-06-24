"""Endpoints del módulo Gestión de Solicitudes."""

import json
from decimal import Decimal, InvalidOperation
from typing import Optional

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.application.interfaces.email_notifier import EmailNotifier
from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.interfaces.user_repository import UserRepository
from app.application.use_cases.solicitudes_gestion import (
    AgregarObservacionSolicitud,
    ArchivoEntradaSolicitud,
    EnviarCotizacionSolicitud,
    GetSolicitudGestion,
    GestionarSolicitudPanel,
    ListarPendientesAprobacion,
    ListarSolicitudesGestion,
    ListarSolicitudesPanelGestion,
    MarcarEntregaSolicitud,
    RegistrarEntregaParcialSolicitud,
    RegistrarSolicitudCompra,
    RegistrarTramiteOcSolicitud,
    ResolverAprobacionSolicitud,
    SolicitarRecotizacionSolicitud,
)
from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionHistorialEstado,
    SolicitudGestionObservacion,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion_producto import LABELS as LABELS_APROB_PRODUCTO
from app.domain.value_objects.estado_aprobacion_producto import EstadoAprobacionProducto
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion
from app.infrastructure.config import settings
from app.presentation.api.v1.dependencies import (
    get_current_user,
    get_file_storage,
    get_email_notifier,
    get_solicitud_gestion_repository,
    get_user_repository,
)
from app.presentation.api.v1.schemas.solicitud_gestion_schemas import (
    RechazarSolicitudGestionBody,
    SolicitudGestionArchivoResponse,
    SolicitudGestionHistorialEstadoResponse,
    SolicitudGestionListItem,
    MarcarEntregaSolicitudResponse,
    EntregaParcialSolicitudResponse,
    SolicitudGestionObservacionResponse,
    SolicitudGestionProductoResponse,
    SolicitudGestionResponse,
)

router = APIRouter(prefix="/solicitudes-gestion", tags=["solicitudes-gestion"])


def _to_producto_item(p) -> SolicitudGestionProductoResponse:
    estado = p.estado_aprobacion
    if isinstance(estado, EstadoAprobacionProducto):
        estado_val = estado.value
    else:
        estado_val = str(estado or EstadoAprobacionProducto.PENDIENTE.value)
    try:
        estado_enum = EstadoAprobacionProducto(estado_val)
    except ValueError:
        estado_enum = EstadoAprobacionProducto.PENDIENTE
    return SolicitudGestionProductoResponse(
        id=p.id,
        codigo_siimed=p.codigo_siimed,
        unidad=p.unidad,
        descripcion=p.descripcion,
        centro_costo=p.centro_costo,
        cantidad=float(p.cantidad) if p.cantidad is not None else 1.0,
        cantidad_entregada=float(p.cantidad_entregada)
        if getattr(p, "cantidad_entregada", None) is not None
        else 0.0,
        cantidad_pendiente=float(p.cantidad_pendiente)
        if getattr(p, "cantidad_pendiente", None) is not None
        else max(
            0.0,
            float(p.cantidad or 1)
            - float(getattr(p, "cantidad_entregada", 0) or 0),
        ),
        estado_entrega=getattr(p, "estado_entrega", "pendiente") or "pendiente",
        estado_aprobacion=estado_enum.value,
        estado_aprobacion_label=LABELS_APROB_PRODUCTO.get(estado_enum, estado_enum.value),
        numero_tramite_oc=getattr(p, "numero_tramite_oc", "") or "",
    )


def _to_list_item(s: SolicitudGestion) -> SolicitudGestionListItem:
    return SolicitudGestionListItem(
        id=s.id,
        codigo=s.codigo,
        tipo=s.tipo,
        titulo=s.titulo,
        presupuestado=s.presupuestado,
        centro_costo_area=s.centro_costo_area,
        lider_area_label=s.lider_area_label,
        estado=s.estado,
        cantidad_productos=s.cantidad_productos,
        cantidad_productos_aprobados=s.cantidad_productos_aprobados,
        aprobacion_parcial=s.aprobacion_parcial,
        tiene_tramite_oc_registrado=s.tiene_tramite_oc_registrado,
        entrega_completa=s.entrega_completa,
        tiene_entrega_pendiente=s.tiene_entrega_pendiente,
        cantidad_archivos=len(s.archivos),
        creado_por_username=s.creado_por_username,
        gestor_id=s.gestor_id,
        gestor_username=s.gestor_username,
        created_at=s.created_at,
    )


def _to_archivo_item(a) -> SolicitudGestionArchivoResponse:
    return SolicitudGestionArchivoResponse(
        id=a.id,
        nombre_original=a.nombre_original,
        mime_type=a.mime_type,
        tamano_bytes=a.tamano_bytes,
        categoria=a.categoria,
        observacion_id=getattr(a, "observacion_id", None),
        created_at=a.created_at,
    )


def _to_observacion_item(o: SolicitudGestionObservacion) -> SolicitudGestionObservacionResponse:
    return SolicitudGestionObservacionResponse(
        id=o.id,
        autor_nombre=o.autor_nombre,
        autor_rol=o.autor_rol,
        autor_etiqueta=o.autor_etiqueta,
        contenido=o.contenido,
        contenido_texto=o.contenido_texto,
        archivos=[_to_archivo_item(a) for a in (o.archivos or [])],
        created_at=o.created_at,
    )


def _to_historial_item(h: SolicitudGestionHistorialEstado) -> SolicitudGestionHistorialEstadoResponse:
    return SolicitudGestionHistorialEstadoResponse(
        id=h.id,
        etapa=h.etapa,
        etapa_label=h.etapa.label,
        usuario_id=h.usuario_id,
        usuario_username=h.usuario_username,
        comentario=h.comentario,
        created_at=h.created_at,
    )


def _to_response(
    s: SolicitudGestion,
    historial: list[SolicitudGestionHistorialEstado] | None = None,
) -> SolicitudGestionResponse:
    return SolicitudGestionResponse(
        id=s.id,
        codigo=s.codigo,
        tipo=s.tipo,
        titulo=s.titulo,
        presupuestado=s.presupuestado,
        centro_costo_area=s.centro_costo_area,
        lider_area_id=s.lider_area_id,
        lider_area_label=s.lider_area_label,
        observaciones=s.observaciones,
        observaciones_texto=s.observaciones_texto,
        observaciones_gestion=s.observaciones_gestion,
        justificacion_cotizaciones=s.justificacion_cotizaciones,
        numero_tramite_oc=s.numero_tramite_oc or "",
        lider_segunda_aprobacion_id=s.lider_segunda_aprobacion_id,
        lider_segunda_aprobacion_label=s.lider_segunda_aprobacion_label,
        gestor_id=s.gestor_id,
        gestor_username=s.gestor_username,
        estado=s.estado,
        creado_por_id=s.creado_por_id,
        creado_por_username=s.creado_por_username,
        created_at=s.created_at,
        updated_at=s.updated_at,
        productos=[_to_producto_item(p) for p in s.productos],
        archivos=[
            _to_archivo_item(a)
            for a in s.archivos
        ],
        historial_estados=[_to_historial_item(h) for h in (historial or [])],
        observaciones_trazabilidad=[
            _to_observacion_item(o) for o in (s.observaciones_trazabilidad or [])
        ],
        aprobacion_parcial=s.aprobacion_parcial,
        cantidad_productos_aprobados=s.cantidad_productos_aprobados,
        tiene_tramite_oc_registrado=s.tiene_tramite_oc_registrado,
        entrega_completa=s.entrega_completa,
        tiene_entrega_pendiente=s.tiene_entrega_pendiente,
    )


@router.get("", response_model=list[SolicitudGestionListItem])
def listar_solicitudes(
    q: Optional[str] = Query(None, description="Buscar por código, título o líder."),
    tipo: Optional[TipoSolicitudGestion] = Query(None),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> list[SolicitudGestionListItem]:
    items = ListarSolicitudesGestion(repo).execute(current, tipo=tipo, query=q)
    return [_to_list_item(s) for s in items]


@router.get("/pendientes-aprobacion", response_model=list[SolicitudGestionListItem])
def listar_pendientes_aprobacion(
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> list[SolicitudGestionListItem]:
    try:
        items = ListarPendientesAprobacion(repo).execute(current)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return [_to_list_item(s) for s in items]


@router.get("/panel-gestion", response_model=list[SolicitudGestionListItem])
def listar_panel_gestion(
    q: Optional[str] = Query(None, description="Buscar por código, título o solicitante."),
    tipo: Optional[TipoSolicitudGestion] = Query(None),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> list[SolicitudGestionListItem]:
    try:
        items = ListarSolicitudesPanelGestion(repo).execute(current, tipo=tipo, query=q)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return [_to_list_item(s) for s in items]


@router.get("/{solicitud_id}/archivos/{archivo_id}")
def descargar_archivo_solicitud(
    solicitud_id: int,
    archivo_id: int,
    inline: bool = Query(False, description="Mostrar en navegador en lugar de descargar."),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> FileResponse:
    try:
        solicitud = GetSolicitudGestion(repo).execute(current, solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    archivo = next((a for a in solicitud.archivos if a.id == archivo_id), None)
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
        content_disposition_type="inline" if inline else "attachment",
    )


@router.get("/{solicitud_id}", response_model=SolicitudGestionResponse)
def obtener_solicitud(
    solicitud_id: int,
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> SolicitudGestionResponse:
    try:
        caso = GetSolicitudGestion(repo)
        solicitud = caso.execute(current, solicitud_id)
        historial = caso.get_historial(current, solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _to_response(solicitud, historial)


@router.post("/compra", response_model=SolicitudGestionResponse, status_code=status.HTTP_201_CREATED)
async def registrar_solicitud_compra(
    titulo: str = Form(...),
    presupuestado: bool = Form(...),
    centro_costo_area: str = Form(...),
    lider_area_id: str = Form(...),
    lider_area_label: str = Form(""),
    observaciones: str = Form(""),
    observaciones_texto: str = Form(""),
    productos_json: str = Form(...),
    archivos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> SolicitudGestionResponse:
    entradas: list[ArchivoEntradaSolicitud] = []
    for upload in archivos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud = RegistrarSolicitudCompra(repo, storage).execute(
            actor=current,
            titulo=titulo,
            presupuestado=presupuestado,
            centro_costo_area=centro_costo_area,
            lider_area_id=lider_area_id,
            lider_area_label=lider_area_label,
            observaciones=observaciones,
            observaciones_texto=observaciones_texto,
            productos_json=productos_json,
            archivos=entradas,
        )
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return _to_response(solicitud)


@router.post("/{solicitud_id}/aprobar", response_model=SolicitudGestionResponse)
async def aprobar_solicitud(
    solicitud_id: int,
    observacion: str = Form(""),
    observacion_texto: str = Form(""),
    tipo_aprobacion: str = Form("total"),
    productos_aprobados: str = Form("[]"),
    productos_cantidades: str = Form("{}"),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> SolicitudGestionResponse:
    entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    productos_ids: list[int] = []
    raw_ids = (productos_aprobados or "").strip()
    if raw_ids:
        try:
            parsed = json.loads(raw_ids)
            if isinstance(parsed, list):
                productos_ids = [int(x) for x in parsed]
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato inválido en productos_aprobados.",
            ) from e

    cantidades_por_id: dict[int, Decimal] = {}
    raw_cantidades = (productos_cantidades or "").strip()
    if raw_cantidades:
        try:
            parsed_cant = json.loads(raw_cantidades)
            if isinstance(parsed_cant, dict):
                for key, value in parsed_cant.items():
                    try:
                        cantidades_por_id[int(key)] = Decimal(str(value))
                    except (InvalidOperation, ValueError, TypeError) as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Formato inválido en productos_cantidades.",
                        ) from e
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Formato inválido en productos_cantidades.",
            ) from e

    try:
        solicitud = ResolverAprobacionSolicitud(repo).aprobar(
            current,
            solicitud_id,
            observacion=observacion,
            observacion_texto=observacion_texto,
            archivos=entradas,
            storage=storage,
            tipo_aprobacion=tipo_aprobacion,
            productos_aprobados_ids=productos_ids,
            productos_cantidades=cantidades_por_id or None,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_response(solicitud)


@router.post("/{solicitud_id}/rechazar", response_model=SolicitudGestionResponse)
def rechazar_solicitud(
    solicitud_id: int,
    body: RechazarSolicitudGestionBody,
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> SolicitudGestionResponse:
    try:
        solicitud = ResolverAprobacionSolicitud(repo).rechazar(
            current, solicitud_id, motivo=body.motivo
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_response(solicitud)


@router.post("/{solicitud_id}/solicitar-recotizacion", response_model=SolicitudGestionResponse)
async def solicitar_recotizacion_solicitud(
    solicitud_id: int,
    observacion: str = Form(""),
    observacion_texto: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> SolicitudGestionResponse:
    entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud = SolicitarRecotizacionSolicitud(repo).execute(
            current,
            solicitud_id,
            observacion=observacion,
            observacion_texto=observacion_texto,
            archivos=entradas,
            storage=storage,
        )
        historial = repo.get_historial(solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_response(solicitud, historial)


@router.post("/{solicitud_id}/gestionar", response_model=SolicitudGestionResponse)
def gestionar_solicitud_panel(
    solicitud_id: int,
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
) -> SolicitudGestionResponse:
    try:
        solicitud = GestionarSolicitudPanel(repo).execute(current, solicitud_id)
        historial = repo.get_historial(solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_response(solicitud, historial)


@router.post("/{solicitud_id}/enviar-cotizacion", response_model=SolicitudGestionResponse)
async def enviar_cotizacion_solicitud(
    solicitud_id: int,
    nueva_observacion: str = Form(""),
    nueva_observacion_texto: str = Form(""),
    justificacion: str = Form(""),
    lider_segunda_aprobacion_id: str = Form(...),
    lider_segunda_aprobacion_label: str = Form(""),
    cotizaciones: list[UploadFile] = File(default=[]),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> SolicitudGestionResponse:
    entradas: list[ArchivoEntradaSolicitud] = []
    for upload in cotizaciones:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    adjuntos_entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        adjuntos_entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud = EnviarCotizacionSolicitud(repo, storage).execute(
            current,
            solicitud_id,
            nueva_observacion=nueva_observacion,
            nueva_observacion_texto=nueva_observacion_texto,
            justificacion=justificacion,
            lider_segunda_aprobacion_id=lider_segunda_aprobacion_id,
            lider_segunda_aprobacion_label=lider_segunda_aprobacion_label,
            cotizaciones=entradas,
            archivos_observacion=adjuntos_entradas,
        )
        historial = repo.get_historial(solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_response(solicitud, historial)


@router.post("/{solicitud_id}/tramite-oc", response_model=SolicitudGestionResponse)
async def registrar_tramite_oc_solicitud(
    solicitud_id: int,
    numero_tramite_oc: str = Form(""),
    productos_tramite_oc: str = Form("{}"),
    nueva_observacion: str = Form(""),
    nueva_observacion_texto: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> SolicitudGestionResponse:
    try:
        raw_map = json.loads(productos_tramite_oc or "{}")
        if not isinstance(raw_map, dict):
            raise ValueError("El formato de trámite parcial por ítem no es válido.")
        numeros_por_producto: dict[int, str] = {}
        for key, value in raw_map.items():
            try:
                numeros_por_producto[int(key)] = str(value or "")
            except (TypeError, ValueError) as exc:
                raise ValueError("Identificador de producto inválido en trámite parcial.") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El JSON de trámite parcial no es válido.",
        ) from exc

    adjuntos_entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        adjuntos_entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud = RegistrarTramiteOcSolicitud(repo, storage).execute(
            current,
            solicitud_id,
            numero_tramite_oc=numero_tramite_oc,
            numeros_por_producto=numeros_por_producto,
            nueva_observacion=nueva_observacion,
            nueva_observacion_texto=nueva_observacion_texto,
            archivos_observacion=adjuntos_entradas,
        )
        historial = repo.get_historial(solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_response(solicitud, historial)


@router.post("/{solicitud_id}/marcar-entrega", response_model=MarcarEntregaSolicitudResponse)
async def marcar_entrega_solicitud(
    solicitud_id: int,
    observacion: str = Form(""),
    observacion_texto: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    users: UserRepository = Depends(get_user_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> MarcarEntregaSolicitudResponse:
    adjuntos_entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        adjuntos_entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud, email_enviado = MarcarEntregaSolicitud(
            repo, users, notifier, storage
        ).execute(
            current,
            solicitud_id,
            observacion=observacion,
            observacion_texto=observacion_texto,
            archivos_observacion=adjuntos_entradas,
        )
        historial = repo.get_historial(solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return MarcarEntregaSolicitudResponse(
        solicitud=_to_response(solicitud, historial),
        email_enviado=email_enviado,
    )


@router.post("/{solicitud_id}/entrega-parcial", response_model=EntregaParcialSolicitudResponse)
async def registrar_entrega_parcial_solicitud(
    solicitud_id: int,
    productos_entrega: str = Form("{}"),
    observacion: str = Form(""),
    observacion_texto: str = Form(""),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    users: UserRepository = Depends(get_user_repository),
    storage: FileStorage = Depends(get_file_storage),
    notifier: EmailNotifier = Depends(get_email_notifier),
) -> EntregaParcialSolicitudResponse:
    try:
        raw_map = json.loads(productos_entrega or "{}")
        if not isinstance(raw_map, dict):
            raise ValueError("El formato de entrega parcial por ítem no es válido.")
        cantidades: dict[int, Decimal] = {}
        for key, value in raw_map.items():
            try:
                cantidad = Decimal(str(value))
            except (InvalidOperation, TypeError) as exc:
                raise ValueError("Cantidad de entrega inválida.") from exc
            if cantidad <= 0:
                continue
            cantidades[int(key)] = cantidad
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El JSON de entrega parcial no es válido.",
        ) from exc

    adjuntos_entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido = await upload.read()
        if len(contenido) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        adjuntos_entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido,
            )
        )

    try:
        solicitud, email_enviado, lineas = RegistrarEntregaParcialSolicitud(
            repo, users, notifier, storage
        ).execute(
            current,
            solicitud_id,
            productos_entrega=cantidades,
            observacion=observacion,
            observacion_texto=observacion_texto,
            archivos_observacion=adjuntos_entradas,
        )
        historial = repo.get_historial(solicitud_id)
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return EntregaParcialSolicitudResponse(
        solicitud=_to_response(solicitud, historial),
        email_enviado=email_enviado,
        lineas_entrega=lineas,
    )


@router.post(
    "/{solicitud_id}/observaciones",
    response_model=SolicitudGestionObservacionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def agregar_observacion_solicitud(
    solicitud_id: int,
    contenido: str = Form(""),
    contenido_texto: str = Form(""),
    contexto_rol: str = Form("default"),
    adjuntos: list[UploadFile] = File(default=[]),
    current: User = Depends(get_current_user),
    repo: SolicitudGestionRepository = Depends(get_solicitud_gestion_repository),
    storage: FileStorage = Depends(get_file_storage),
) -> SolicitudGestionObservacionResponse:
    entradas: list[ArchivoEntradaSolicitud] = []
    for upload in adjuntos:
        if not upload.filename:
            continue
        contenido_bin = await upload.read()
        if len(contenido_bin) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"El archivo '{upload.filename}' supera el límite permitido.",
            )
        entradas.append(
            ArchivoEntradaSolicitud(
                nombre_original=upload.filename,
                mime_type=upload.content_type or "application/octet-stream",
                contenido=contenido_bin,
            )
        )

    try:
        observacion = AgregarObservacionSolicitud(repo, storage).execute(
            current,
            solicitud_id,
            contenido=contenido,
            contenido_texto=contenido_texto,
            contexto_rol=contexto_rol or "default",
            archivos=entradas,
        )
    except ContratoNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_observacion_item(observacion)
