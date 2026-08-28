"""Caso de uso: radicar una solicitud de contrato.

Encapsula las reglas de negocio:
- Compras y Admin pueden radicar contratos u órdenes de trabajo.
- Jurídica sólo puede radicar contratos.
- La compañía siempre es Colbeef.
- Deben adjuntarse los 3 archivos obligatorios.
- El archivo opcional (1 más) puede o no enviarse.
- La solicitud queda pendiente de aprobación del líder de proceso.
"""

from dataclasses import dataclass
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.domain.entities.contrato import (
    COMPANIA_DEFAULT,
    PLAZO_MAXIMO,
    VALOR_MAXIMO,
    ArchivoAdjunto,
    Contrato,
    TIPO_CODIGO_CONTRATO,
    TipoArchivo,
    normalizar_tipo_codigo,
    sumar_dias_habiles,
)
from app.domain.entities.user import User
from app.domain.exceptions import (
    ContratoNotFoundError,
    MissingRequiredFileError,
    UnauthorizedError,
)
from app.domain.value_objects.calendario_colombia import siguiente_dia_habil
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_precio import TipoPrecio
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios
from app.domain.value_objects.unidad_plazo import UnidadPlazo


@dataclass
class ArchivoEntrada:
    tipo: TipoArchivo
    nombre_original: str
    mime_type: str
    contenido: bytes


def _cotizacion_elegida(solicitud_origen):
    for archivo in getattr(solicitud_origen, "archivos", None) or []:
        if (
            getattr(archivo, "categoria", "") == "cotizacion"
            and getattr(archivo, "propuesta", False)
        ):
            return archivo
    return None


def _entrada_cotizacion_desde_srv(solicitud_origen, storage: FileStorage) -> ArchivoEntrada | None:
    elegido = _cotizacion_elegida(solicitud_origen)
    if elegido is None:
        return None
    contenido = storage.read(elegido.ruta_almacenamiento)
    return ArchivoEntrada(
        tipo=TipoArchivo.COTIZACION,
        nombre_original=elegido.nombre_original,
        mime_type=elegido.mime_type or "application/octet-stream",
        contenido=contenido,
    )


def _snapshot_anticipo(solicitud_origen) -> dict:
    """Copia los datos de anticipo de la SRV para fijarlos en el contrato.

    Si el contrato no nace de una SRV, queda sin anticipo.
    """
    if solicitud_origen is None:
        return {
            "requiere_anticipo": False,
            "porcentaje_anticipo": None,
            "monto_anticipo": None,
            "observaciones_anticipo": "",
        }
    return {
        "requiere_anticipo": bool(getattr(solicitud_origen, "requiere_anticipo", False)),
        "porcentaje_anticipo": getattr(solicitud_origen, "porcentaje_anticipo", None),
        "monto_anticipo": getattr(solicitud_origen, "monto_anticipo", None),
        "observaciones_anticipo": getattr(solicitud_origen, "observaciones_anticipo", "") or "",
    }


def _validar_actor_y_tipo(actor: User, tipo_codigo: str) -> str:
    tipo = normalizar_tipo_codigo(tipo_codigo)
    if not (actor.is_compras() or actor.is_juridica() or actor.is_admin()):
        raise UnauthorizedError(
            "Sólo usuarios de Compras, Jurídica o Admin pueden radicar solicitudes."
        )
    if actor.is_juridica() and tipo != TIPO_CODIGO_CONTRATO:
        raise UnauthorizedError("Jurídica sólo puede radicar contratos.")
    return tipo


class RadicarSolicitud:
    def __init__(
        self,
        contratos: ContratoRepository,
        storage: FileStorage,
        solicitudes: SolicitudGestionRepository | None = None,
    ) -> None:
        self._contratos = contratos
        self._storage = storage
        self._solicitudes = solicitudes

    def execute(
        self,
        actor: User,
        proveedor_contratista: str,
        nit_proveedor: str,
        proveedor_email: str,
        descripcion_servicio: str,
        obligaciones_colbeef: str,
        obligaciones_proveedor: str,
        valor: Decimal,
        moneda: Moneda,
        plazo_cantidad: int,
        plazo_unidad: UnidadPlazo,
        renovacion_automatica: bool,
        condiciones_recibido_satisfactorio: str,
        requiere_poliza: bool,
        tipo_precio: TipoPrecio,
        forma_pago: str,
        centro_costos: str,
        correo_lider_proceso: str,
        correo_gerencia: str,
        tipo_codigo: str,
        archivos: list[ArchivoEntrada],
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        fecha_proxima_notificacion: date | None = None,
        solicitud_gestion_id: int | None = None,
        supervisor_id: int | None = None,
    ) -> Contrato:
        tipo_codigo = _validar_actor_y_tipo(actor, tipo_codigo)

        solicitud_origen = None
        solicitud_codigo = ""
        if solicitud_gestion_id is not None:
            solicitud_origen, solicitud_codigo = self._resolver_solicitud_origen(
                actor, solicitud_gestion_id
            )
            if not any(a.tipo == TipoArchivo.COTIZACION for a in archivos):
                extra = _entrada_cotizacion_desde_srv(solicitud_origen, self._storage)
                if extra is not None:
                    archivos.append(extra)

        self._validar_archivos_obligatorios(archivos)
        self._validar_campos(
            proveedor_contratista=proveedor_contratista,
            nit_proveedor=nit_proveedor,
            descripcion_servicio=descripcion_servicio,
            obligaciones_colbeef=obligaciones_colbeef,
            obligaciones_proveedor=obligaciones_proveedor,
            valor=valor,
            plazo_cantidad=plazo_cantidad,
            condiciones_recibido_satisfactorio=condiciones_recibido_satisfactorio.strip(),
            correo_lider_proceso=correo_lider_proceso,
            correo_gerencia=correo_gerencia,
        )
        forma_pago_limpia = (forma_pago or "").strip()
        if not forma_pago_limpia:
            raise ValueError("La forma de pago es obligatoria.")
        centro_costos_limpio = (centro_costos or "").strip()
        if not centro_costos_limpio:
            raise ValueError("El centro de costos es obligatorio.")

        # Snapshot del anticipo gestionado en la SRV (queda fijo en el contrato).
        anticipo = _snapshot_anticipo(solicitud_origen)

        fecha_fin_calculada = fecha_fin
        if fecha_inicio and fecha_fin_calculada is None:
            fecha_fin_calculada = calcular_fecha_fin(
                fecha_inicio,
                plazo_cantidad,
                plazo_unidad,
            )
        if fecha_inicio and fecha_fin_calculada and fecha_fin_calculada < fecha_inicio:
            raise ValueError("La fecha de vencimiento no puede ser anterior a la fecha de inicio.")
        if fecha_proxima_notificacion is None and fecha_fin_calculada:
            fecha_proxima_notificacion = max(
                fecha_inicio or fecha_fin_calculada,
                fecha_fin_calculada - timedelta(days=30),
            )

        contrato = Contrato(
            compania=COMPANIA_DEFAULT,
            proveedor_contratista=proveedor_contratista.strip(),
            nit_proveedor=nit_proveedor.strip(),
            proveedor_email=(proveedor_email or "").strip(),
            descripcion_servicio=descripcion_servicio.strip(),
            obligaciones_colbeef=obligaciones_colbeef.strip(),
            obligaciones_proveedor=obligaciones_proveedor.strip(),
            valor=valor,
            moneda=moneda,
            plazo_cantidad=plazo_cantidad,
            plazo_unidad=plazo_unidad,
            renovacion_automatica=renovacion_automatica,
            condiciones_recibido_satisfactorio=condiciones_recibido_satisfactorio.strip(),
            requiere_poliza=requiere_poliza,
            tipo_precio=tipo_precio,
            forma_pago=forma_pago_limpia,
            centro_costos=centro_costos_limpio,
            supervisor_id=supervisor_id,
            requiere_anticipo=anticipo["requiere_anticipo"],
            porcentaje_anticipo=anticipo["porcentaje_anticipo"],
            monto_anticipo=anticipo["monto_anticipo"],
            observaciones_anticipo=anticipo["observaciones_anticipo"],
            creado_por_id=actor.id,
            correo_lider_proceso=correo_lider_proceso.strip(),
            correo_gerencia=correo_gerencia.strip(),
            tipo_codigo=tipo_codigo,
            # La aprobación Líder→Gerencia ya se hace en la Solicitud de Servicio,
            # así que el contrato nace aprobado y pasa directo a Jurídica.
            estado_aprobacion=EstadoAprobacion.APROBADO,
            solicitud_gestion_id=solicitud_origen.id if solicitud_origen else None,
            solicitud_gestion_codigo=solicitud_codigo,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin_calculada,
            fecha_proxima_notificacion=fecha_proxima_notificacion,
        )

        for entrada in archivos:
            stored = self._storage.save(
                contenido=entrada.contenido,
                nombre_original=entrada.nombre_original,
                mime_type=entrada.mime_type,
                subcarpeta="contratos",
            )
            contrato.archivos.append(
                ArchivoAdjunto(
                    tipo=entrada.tipo,
                    nombre_original=stored.nombre_original,
                    ruta_almacenamiento=stored.ruta,
                    mime_type=stored.mime_type,
                    tamano_bytes=stored.tamano_bytes,
                )
            )

        creado = self._contratos.create(contrato)
        if solicitud_origen is not None and self._solicitudes is not None:
            self._vincular_solicitud(actor, solicitud_origen, creado)
        return creado

    def _resolver_solicitud_origen(self, actor: User, solicitud_gestion_id: int):
        if self._solicitudes is None:
            raise ValueError(
                "No se puede vincular la solicitud de servicios: repositorio no disponible."
            )
        solicitud = self._solicitudes.get_by_id(solicitud_gestion_id)
        if solicitud is None:
            raise ContratoNotFoundError(
                f"No existe la solicitud de gestión {solicitud_gestion_id}."
            )
        if not es_flujo_servicios(solicitud.tipo):
            raise ValueError(
                "Solo se pueden vincular solicitudes de servicios (SRV) a un contrato/OT."
            )
        if solicitud.contrato_id:
            raise ValueError(
                f"La solicitud {solicitud.codigo} ya está vinculada al documento "
                f"{solicitud.contrato_codigo or solicitud.contrato_id}."
            )
        if not (
            actor.is_admin()
            or actor.is_compras()
        ):
            raise UnauthorizedError(
                "No tienes permiso para vincular esta solicitud de servicios."
            )
        return solicitud, solicitud.codigo or ""

    def _vincular_solicitud(self, actor: User, solicitud, contrato: Contrato) -> None:
        assert self._solicitudes is not None
        solicitud.contrato_id = contrato.id
        solicitud.contrato_codigo = contrato.codigo or ""
        self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud.id,
            EstadoSolicitudGestion.EN_JURIDICA,
            usuario_id=actor.id,
            comentario=(
                f"Documento {contrato.codigo} radicado y vinculado a {solicitud.codigo}"
            ),
        )

    @staticmethod
    def _validar_archivos_obligatorios(archivos: list[ArchivoEntrada]) -> None:
        tipos_presentes = {a.tipo for a in archivos}
        faltantes = [
            t for t in TipoArchivo.obligatorios_radicacion()
            if t not in tipos_presentes
        ]
        if faltantes:
            nombres = ", ".join(t.value for t in faltantes)
            raise MissingRequiredFileError(f"Faltan archivos obligatorios: {nombres}")

    @staticmethod
    def _validar_campos(
        proveedor_contratista: str,
        nit_proveedor: str,
        descripcion_servicio: str,
        obligaciones_colbeef: str,
        obligaciones_proveedor: str,
        valor: Decimal,
        plazo_cantidad: int,
        condiciones_recibido_satisfactorio: str,
        correo_lider_proceso: str,
        correo_gerencia: str,
    ) -> None:
        obligatorios_texto = {
            "proveedor_contratista": proveedor_contratista,
            "nit_proveedor": nit_proveedor,
            "descripcion_servicio": descripcion_servicio,
            "obligaciones_colbeef": obligaciones_colbeef,
            "obligaciones_proveedor": obligaciones_proveedor,
            "condiciones_recibido_satisfactorio": condiciones_recibido_satisfactorio,
            "correo_lider_proceso": correo_lider_proceso,
            "correo_gerencia": correo_gerencia,
        }
        for nombre, valor_campo in obligatorios_texto.items():
            if not valor_campo or not str(valor_campo).strip():
                raise ValueError(f"El campo '{nombre}' es obligatorio.")

        if valor is None or Decimal(valor) <= 0:
            raise ValueError("El valor del contrato debe ser mayor a 0.")
        if Decimal(valor) > VALOR_MAXIMO:
            raise ValueError(
                "El valor del contrato es demasiado grande. "
                f"El máximo permitido es {VALOR_MAXIMO:,.2f}."
            )
        if plazo_cantidad is None or plazo_cantidad <= 0:
            raise ValueError("La cantidad de plazo debe ser mayor a 0.")
        if plazo_cantidad > PLAZO_MAXIMO:
            raise ValueError("La cantidad de plazo es demasiado grande.")


def calcular_fecha_fin(
    fecha_inicio: date,
    plazo_cantidad: int,
    plazo_unidad: UnidadPlazo,
) -> date:
    if plazo_unidad == UnidadPlazo.DIAS_CALENDARIO:
        return fecha_inicio + timedelta(days=plazo_cantidad)
    if plazo_unidad == UnidadPlazo.DIAS:
        return sumar_dias_habiles(fecha_inicio, plazo_cantidad)

    meses = plazo_cantidad if plazo_unidad == UnidadPlazo.MESES else plazo_cantidad * 12
    mes_base = fecha_inicio.month - 1 + meses
    anio = fecha_inicio.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(fecha_inicio.day, monthrange(anio, mes)[1])
    return siguiente_dia_habil(date(anio, mes, dia))
