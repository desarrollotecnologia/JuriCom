"""Caso de uso: buzón de pendientes agrupado por módulo."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.use_cases.contratos.buscar_contratos import BuscarContratos
from app.domain.entities.contrato import Contrato
from app.domain.entities.otrosi import Otrosi
from app.domain.entities.user import User
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato


class PrioridadTarea(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


_PRIORIDAD_ORDEN = {
    PrioridadTarea.ALTA: 0,
    PrioridadTarea.MEDIA: 1,
    PrioridadTarea.BAJA: 2,
}


@dataclass
class Tarea:
    id: str
    tipo: str
    titulo: str
    descripcion: str
    prioridad: PrioridadTarea
    contrato_id: int
    contrato_codigo: Optional[str]
    proveedor: str
    fecha_referencia: Optional[date]
    accion_url: str
    otrosi_id: Optional[int] = None
    otrosi_numero: Optional[int] = None


@dataclass
class GrupoTareas:
    clave: str
    titulo: str
    descripcion: str
    tareas: list[Tarea] = field(default_factory=list)


@dataclass
class ModuloPendiente:
    titulo: str
    descripcion: str
    cantidad: int
    alta_prioridad: int
    accion_url: str


@dataclass
class Buzon:
    total: int
    alta_prioridad: int
    modulos: list[ModuloPendiente]


def _destino_modulo(clave: str, actor: User) -> tuple[str, str, str]:
    """Devuelve título, descripción y URL del módulo destino."""
    juridica_pendientes = (
        "Pendientes Jurídica",
        "Contratos aprobados que requieren revisión, póliza o activación.",
        "/app/juridica/pendientes.html",
    )
    mapa: dict[str, tuple[str, str, str]] = {
        "sin_poliza": juridica_pendientes,
        "listo_activar": juridica_pendientes,
        "contrato_pendiente_juridica": juridica_pendientes,
        "otrosi_pendiente_juridica": (
            "Otrosíes pendientes",
            "Otrosíes aprobados que esperan el PDF firmado.",
            "/app/juridica/otrosies-pendientes.html",
        ),
        "vence_pronto": (
            "Edición de contratos",
            "Contratos por vencer o con notificación programada.",
            "/app/juridica/editar-contrato.html",
        ),
        "notificacion_hoy": (
            "Edición de contratos",
            "Contratos por vencer o con notificación programada.",
            "/app/juridica/editar-contrato.html",
        ),
        "solicitud_rechazada": (
            "Mis solicitudes",
            "Solicitudes rechazadas o en proceso de aprobación.",
            "/app/compras/mis-solicitudes.html",
        ),
        "solicitud_en_aprobacion": (
            "Mis solicitudes",
            "Solicitudes rechazadas o en proceso de aprobación.",
            "/app/compras/mis-solicitudes.html",
        ),
        "otrosi_en_aprobacion": (
            "Mis solicitudes",
            "Solicitudes rechazadas o en proceso de aprobación.",
            "/app/compras/mis-solicitudes.html",
        ),
        "aprobacion_pendiente": (
            "Contratos",
            "Solicitudes del sistema en aprobación o rechazadas.",
            "/app/compras/mis-solicitudes.html",
        ),
    }

    titulo, descripcion, url = mapa[clave]

    if clave in ("vence_pronto", "notificacion_hoy") and actor.is_compras():
        return (
            "Mis solicitudes",
            "Tus contratos por vencer o con seguimiento pendiente.",
            "/app/compras/mis-solicitudes.html",
        )

    return titulo, descripcion, url


def _agrupar_en_modulos(grupos: list[GrupoTareas], actor: User) -> list[ModuloPendiente]:
    por_url: dict[str, ModuloPendiente] = {}

    for grupo in grupos:
        if not grupo.tareas:
            continue
        titulo, descripcion, url = _destino_modulo(grupo.clave, actor)
        alta = sum(1 for t in grupo.tareas if t.prioridad == PrioridadTarea.ALTA)

        if actor.is_admin() and url == "/app/compras/mis-solicitudes.html":
            titulo = "Contratos"
            descripcion = "Solicitudes del sistema en aprobación o rechazadas."

        if url in por_url:
            existente = por_url[url]
            existente.cantidad += len(grupo.tareas)
            existente.alta_prioridad += alta
        else:
            por_url[url] = ModuloPendiente(
                titulo=titulo,
                descripcion=descripcion,
                cantidad=len(grupo.tareas),
                alta_prioridad=alta,
                accion_url=url,
            )

    return sorted(
        por_url.values(),
        key=lambda m: (-m.alta_prioridad, -m.cantidad, m.titulo),
    )


def _dias_para_vencer(contrato: Contrato) -> Optional[int]:
    if not contrato.fecha_fin:
        return None
    return (contrato.fecha_fin - date.today()).days


def _umbral_vencimiento(contrato: Contrato) -> int:
    if not contrato.fecha_inicio or not contrato.fecha_fin:
        return 30
    duracion = (contrato.fecha_fin - contrato.fecha_inicio).days
    return 7 if duracion <= 30 else 30


def _alerta_vencimiento(contrato: Contrato) -> bool:
    dias = _dias_para_vencer(contrato)
    return (
        contrato.estado == EstadoContrato.ACTIVO
        and dias is not None
        and 0 <= dias <= _umbral_vencimiento(contrato)
    )


def _codigo(contrato: Contrato) -> str:
    return contrato.codigo or f"#{contrato.id}"


def _url_editar(contrato: Contrato) -> str:
    if contrato.codigo:
        return f"/app/juridica/editar-contrato.html?codigo={contrato.codigo}"
    return "/app/juridica/pendientes.html"


def _url_mis_solicitudes(contrato_id: int) -> str:
    return f"/app/compras/mis-solicitudes.html?contrato={contrato_id}"


def _ordenar_tareas(tareas: list[Tarea]) -> list[Tarea]:
    return sorted(
        tareas,
        key=lambda t: (
            _PRIORIDAD_ORDEN[t.prioridad],
            t.fecha_referencia or date.max,
            t.contrato_id,
        ),
    )


class ObtenerBuzon:
    def __init__(self, contratos: ContratoRepository) -> None:
        self._contratos = contratos

    def execute(self, actor: User) -> Buzon:
        items = BuscarContratos(self._contratos).execute(actor=actor)
        grupos: list[GrupoTareas] = []

        if actor.is_juridica() or actor.is_admin():
            grupos.extend(self._grupos_juridica(items))

        if actor.is_compras() or actor.is_admin():
            grupos.extend(
                self._grupos_compras(
                    items,
                    solo_propios=actor.is_compras(),
                    incluir_en_aprobacion=not actor.is_admin(),
                    incluir_vencimientos=not (actor.is_admin() or actor.is_juridica()),
                )
            )

        if actor.is_admin():
            grupos.extend(self._grupos_admin(items))

        grupos = [g for g in grupos if g.tareas]
        for grupo in grupos:
            grupo.tareas = _ordenar_tareas(grupo.tareas)

        todas = [t for g in grupos for t in g.tareas]
        modulos = _agrupar_en_modulos(grupos, actor)
        return Buzon(
            total=len(todas),
            alta_prioridad=sum(1 for t in todas if t.prioridad == PrioridadTarea.ALTA),
            modulos=modulos,
        )

    def _grupos_juridica(self, items: list[Contrato]) -> list[GrupoTareas]:
        pendientes: list[Tarea] = []
        sin_poliza: list[Tarea] = []
        listos_activar: list[Tarea] = []
        otrosies: list[Tarea] = []
        vencimientos: list[Tarea] = []
        notificaciones: list[Tarea] = []
        hoy = date.today()

        for c in items:
            codigo = _codigo(c)

            if (
                c.estado_aprobacion == EstadoAprobacion.APROBADO
                and c.estado == EstadoContrato.EN_PROCESO
            ):
                pendientes.append(
                    Tarea(
                        id=f"contrato:{c.id}:pendiente_juridica",
                        tipo="contrato_pendiente_juridica",
                        titulo=f"Revisar {codigo}",
                        descripcion=f"{c.proveedor_contratista} — pendiente de revisión jurídica.",
                        prioridad=PrioridadTarea.BAJA,
                        contrato_id=c.id,
                        contrato_codigo=c.codigo,
                        proveedor=c.proveedor_contratista,
                        fecha_referencia=c.created_at.date() if c.created_at else None,
                        accion_url="/app/juridica/pendientes.html",
                    )
                )

                if c.requiere_poliza_y_no_la_tiene():
                    sin_poliza.append(
                        Tarea(
                            id=f"contrato:{c.id}:sin_poliza",
                            tipo="sin_poliza",
                            titulo=f"Subir póliza — {codigo}",
                            descripcion=(
                                f"{c.proveedor_contratista} requiere póliza para poder activarse."
                            ),
                            prioridad=PrioridadTarea.ALTA,
                            contrato_id=c.id,
                            contrato_codigo=c.codigo,
                            proveedor=c.proveedor_contratista,
                            fecha_referencia=None,
                            accion_url="/app/juridica/pendientes.html",
                        )
                    )

                if (
                    (not c.requiere_poliza or c.tiene_poliza())
                    and c.tiene_borrador()
                ):
                    listos_activar.append(
                        Tarea(
                            id=f"contrato:{c.id}:listo_activar",
                            tipo="listo_activar",
                            titulo=f"Activar contrato — {codigo}",
                            descripcion=(
                                f"{c.proveedor_contratista} tiene borrador y puede pasar a activo."
                            ),
                            prioridad=PrioridadTarea.MEDIA,
                            contrato_id=c.id,
                            contrato_codigo=c.codigo,
                            proveedor=c.proveedor_contratista,
                            fecha_referencia=None,
                            accion_url=_url_editar(c),
                        )
                    )

            if _alerta_vencimiento(c):
                dias = _dias_para_vencer(c)
                vencimientos.append(
                    Tarea(
                        id=f"contrato:{c.id}:vence_pronto",
                        tipo="vence_pronto",
                        titulo=f"Vence en {dias} días — {codigo}",
                        descripcion=(
                            f"{c.proveedor_contratista} vence el {c.fecha_fin.isoformat()}."
                        ),
                        prioridad=(
                            PrioridadTarea.ALTA
                            if dias is not None and dias <= 7
                            else PrioridadTarea.MEDIA
                        ),
                        contrato_id=c.id,
                        contrato_codigo=c.codigo,
                        proveedor=c.proveedor_contratista,
                        fecha_referencia=c.fecha_fin,
                        accion_url=_url_editar(c),
                    )
                )

            if (
                c.fecha_proxima_notificacion
                and c.fecha_proxima_notificacion <= hoy
                and c.estado in (EstadoContrato.ACTIVO, EstadoContrato.EN_PROCESO)
            ):
                notificaciones.append(
                    Tarea(
                        id=f"contrato:{c.id}:notificacion_hoy",
                        tipo="notificacion_hoy",
                        titulo=f"Notificación programada — {codigo}",
                        descripcion=(
                            f"Revisar o notificar vencimiento de {c.proveedor_contratista}."
                        ),
                        prioridad=PrioridadTarea.MEDIA,
                        contrato_id=c.id,
                        contrato_codigo=c.codigo,
                        proveedor=c.proveedor_contratista,
                        fecha_referencia=c.fecha_proxima_notificacion,
                        accion_url=_url_editar(c),
                    )
                )

        for c, o in self._contratos.list_otrosies_by_estado_aprobacion(
            EstadoAprobacion.APROBADO
        ):
            if o.archivo_id is not None or o.aprobado_gerencia_at is None:
                continue
            codigo = _codigo(c)
            otrosies.append(
                Tarea(
                    id=f"otrosi:{o.id}:pendiente_juridica",
                    tipo="otrosi_pendiente_juridica",
                    titulo=f"Finalizar otrosí #{o.numero} — {codigo}",
                    descripcion=(
                        f"{c.proveedor_contratista}: {o.tipo.label} — adjuntar PDF firmado."
                    ),
                    prioridad=PrioridadTarea.MEDIA,
                    contrato_id=c.id,
                    contrato_codigo=c.codigo,
                    proveedor=c.proveedor_contratista,
                    fecha_referencia=o.created_at.date() if o.created_at else None,
                    accion_url="/app/juridica/otrosies-pendientes.html",
                    otrosi_id=o.id,
                    otrosi_numero=o.numero,
                )
            )

        return [
            GrupoTareas(
                clave="sin_poliza",
                titulo="Sin póliza",
                descripcion="Contratos que requieren póliza para activarse.",
                tareas=sin_poliza,
            ),
            GrupoTareas(
                clave="listo_activar",
                titulo="Listos para activar",
                descripcion="Contratos con documentación completa pendientes de activación.",
                tareas=listos_activar,
            ),
            GrupoTareas(
                clave="otrosi_pendiente_juridica",
                titulo="Otrosíes por finalizar",
                descripcion="Otrosíes aprobados que esperan el PDF firmado de Jurídica.",
                tareas=otrosies,
            ),
            GrupoTareas(
                clave="vence_pronto",
                titulo="Próximos a vencer",
                descripcion="Contratos activos cerca de su fecha de finalización.",
                tareas=vencimientos,
            ),
            GrupoTareas(
                clave="notificacion_hoy",
                titulo="Notificaciones programadas",
                descripcion="Contratos con fecha de notificación hoy o vencida.",
                tareas=notificaciones,
            ),
            GrupoTareas(
                clave="contrato_pendiente_juridica",
                titulo="Pendientes de revisión",
                descripcion="Contratos aprobados que requieren trabajo de Jurídica.",
                tareas=pendientes,
            ),
        ]

    def _grupos_compras(
        self,
        items: list[Contrato],
        *,
        solo_propios: bool,
        incluir_en_aprobacion: bool = True,
        incluir_vencimientos: bool = True,
    ) -> list[GrupoTareas]:
        en_aprobacion: list[Tarea] = []
        rechazadas: list[Tarea] = []
        otrosies_aprobacion: list[Tarea] = []
        vencimientos: list[Tarea] = []

        for c in items:
            if solo_propios and not c.creado_por_id:
                continue

            codigo = _codigo(c)

            if (
                incluir_en_aprobacion
                and c.estado_aprobacion
                in (
                    EstadoAprobacion.PENDIENTE_LIDER,
                    EstadoAprobacion.PENDIENTE_GERENCIA,
                )
            ):
                paso = c.estado_aprobacion.label
                en_aprobacion.append(
                    Tarea(
                        id=f"contrato:{c.id}:en_aprobacion",
                        tipo="solicitud_en_aprobacion",
                        titulo=f"En aprobación — {codigo}",
                        descripcion=f"{c.proveedor_contratista} — {paso}.",
                        prioridad=PrioridadTarea.MEDIA,
                        contrato_id=c.id,
                        contrato_codigo=c.codigo,
                        proveedor=c.proveedor_contratista,
                        fecha_referencia=c.created_at.date() if c.created_at else None,
                        accion_url=_url_mis_solicitudes(c.id),
                    )
                )

            if c.estado_aprobacion == EstadoAprobacion.RECHAZADO:
                rechazadas.append(
                    Tarea(
                        id=f"contrato:{c.id}:rechazada",
                        tipo="solicitud_rechazada",
                        titulo=f"Solicitud rechazada — {codigo}",
                        descripcion=(
                            f"{c.proveedor_contratista} fue rechazada. Revisa y radica de nuevo."
                        ),
                        prioridad=PrioridadTarea.ALTA,
                        contrato_id=c.id,
                        contrato_codigo=c.codigo,
                        proveedor=c.proveedor_contratista,
                        fecha_referencia=c.updated_at.date() if c.updated_at else None,
                        accion_url=_url_mis_solicitudes(c.id),
                    )
                )

            if incluir_vencimientos and _alerta_vencimiento(c):
                dias = _dias_para_vencer(c)
                vencimientos.append(
                    Tarea(
                        id=f"contrato:{c.id}:vence_pronto",
                        tipo="vence_pronto",
                        titulo=f"Vence en {dias} días — {codigo}",
                        descripcion=(
                            f"{c.proveedor_contratista} vence el {c.fecha_fin.isoformat()}."
                        ),
                        prioridad=(
                            PrioridadTarea.ALTA
                            if dias is not None and dias <= 7
                            else PrioridadTarea.MEDIA
                        ),
                        contrato_id=c.id,
                        contrato_codigo=c.codigo,
                        proveedor=c.proveedor_contratista,
                        fecha_referencia=c.fecha_fin,
                        accion_url=_url_mis_solicitudes(c.id),
                    )
                )

            for o in c.otrosies:
                tarea = self._tarea_otrosi_aprobacion(c, o)
                if tarea:
                    otrosies_aprobacion.append(tarea)

        return [
            GrupoTareas(
                clave="solicitud_rechazada",
                titulo="Solicitudes rechazadas",
                descripcion="Contratos rechazados en el flujo de aprobación.",
                tareas=rechazadas,
            ),
            GrupoTareas(
                clave="solicitud_en_aprobacion",
                titulo="En aprobación",
                descripcion="Solicitudes esperando aprobación de líder o gerencia.",
                tareas=en_aprobacion,
            ),
            GrupoTareas(
                clave="otrosi_en_aprobacion",
                titulo="Otrosíes en aprobación",
                descripcion="Otrosíes esperando aprobación por correo.",
                tareas=otrosies_aprobacion,
            ),
            GrupoTareas(
                clave="vence_pronto",
                titulo="Próximos a vencer",
                descripcion="Tus contratos activos cerca de su fecha de finalización.",
                tareas=vencimientos,
            ),
        ]

    def _tarea_otrosi_aprobacion(self, contrato: Contrato, otrosi: Otrosi) -> Optional[Tarea]:
        if otrosi.estado_aprobacion not in (
            EstadoAprobacion.PENDIENTE_LIDER,
            EstadoAprobacion.PENDIENTE_GERENCIA,
        ):
            return None
        codigo = _codigo(contrato)
        return Tarea(
            id=f"otrosi:{otrosi.id}:en_aprobacion",
            tipo="otrosi_en_aprobacion",
            titulo=f"Otrosí #{otrosi.numero} en aprobación — {codigo}",
            descripcion=f"{contrato.proveedor_contratista} — {otrosi.estado_aprobacion.label}.",
            prioridad=PrioridadTarea.MEDIA,
            contrato_id=contrato.id,
            contrato_codigo=contrato.codigo,
            proveedor=contrato.proveedor_contratista,
            fecha_referencia=otrosi.created_at.date() if otrosi.created_at else None,
            accion_url=f"/app/compras/otrosi.html?contrato_id={contrato.id}",
            otrosi_id=otrosi.id,
            otrosi_numero=otrosi.numero,
        )

    def _grupos_admin(self, items: list[Contrato]) -> list[GrupoTareas]:
        aprobacion: list[Tarea] = []

        for c in items:
            if c.estado_aprobacion not in (
                EstadoAprobacion.PENDIENTE_LIDER,
                EstadoAprobacion.PENDIENTE_GERENCIA,
            ):
                continue
            codigo = _codigo(c)
            aprobacion.append(
                Tarea(
                    id=f"contrato:{c.id}:aprobacion_sistema",
                    tipo="aprobacion_pendiente",
                    titulo=f"Aprobación pendiente — {codigo}",
                    descripcion=f"{c.proveedor_contratista} — {c.estado_aprobacion.label}.",
                    prioridad=PrioridadTarea.MEDIA,
                    contrato_id=c.id,
                    contrato_codigo=c.codigo,
                    proveedor=c.proveedor_contratista,
                    fecha_referencia=c.created_at.date() if c.created_at else None,
                    accion_url=_url_mis_solicitudes(c.id),
                )
            )

        return [
            GrupoTareas(
                clave="aprobacion_pendiente",
                titulo="Aprobaciones en curso",
                descripcion="Contratos del sistema esperando aprobación por correo.",
                tareas=aprobacion,
            ),
        ]


ObtenerBandejaTareas = ObtenerBuzon
