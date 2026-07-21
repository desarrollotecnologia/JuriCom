"""Caso de uso: radicar una solicitud de contrato (rol Compras).

Encapsula las reglas de negocio:
- Sólo Compras o Admin pueden radicar.
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
    TipoArchivo,
    normalizar_tipo_codigo,
)
from app.domain.entities.user import User
from app.domain.exceptions import (
    ContratoNotFoundError,
    MissingRequiredFileError,
    UnauthorizedError,
)
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios
from app.domain.value_objects.unidad_plazo import UnidadPlazo


@dataclass
class ArchivoEntrada:
    tipo: TipoArchivo
    nombre_original: str
    mime_type: str
    contenido: bytes


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
        correo_lider_proceso: str,
        correo_gerencia: str,
        tipo_codigo: str,
        archivos: list[ArchivoEntrada],
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        fecha_proxima_notificacion: date | None = None,
        solicitud_gestion_id: int | None = None,
    ) -> Contrato:
        if not (actor.is_compras() or actor.is_admin()):
            raise UnauthorizedError(
                "Sólo usuarios de Compras (o Admin) pueden radicar solicitudes."
            )

        self._validar_archivos_obligatorios(archivos)
        self._validar_campos(
            proveedor_contratista=proveedor_contratista,
            nit_proveedor=nit_proveedor,
            descripcion_servicio=descripcion_servicio,
            obligaciones_colbeef=obligaciones_colbeef,
            obligaciones_proveedor=obligaciones_proveedor,
            valor=valor,
            plazo_cantidad=plazo_cantidad,
            condiciones_recibido_satisfactorio=condiciones_recibido_satisfactorio,
            correo_lider_proceso=correo_lider_proceso,
            correo_gerencia=correo_gerencia,
        )

        solicitud_origen = None
        solicitud_codigo = ""
        if solicitud_gestion_id is not None:
            solicitud_origen, solicitud_codigo = self._resolver_solicitud_origen(
                actor, solicitud_gestion_id
            )

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
            creado_por_id=actor.id,
            correo_lider_proceso=correo_lider_proceso.strip(),
            correo_gerencia=correo_gerencia.strip(),
            tipo_codigo=normalizar_tipo_codigo(tipo_codigo),
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
            solicitud.estado,
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
    if plazo_unidad == UnidadPlazo.DIAS:
        return fecha_inicio + timedelta(days=plazo_cantidad)

    meses = plazo_cantidad if plazo_unidad == UnidadPlazo.MESES else plazo_cantidad * 12
    mes_base = fecha_inicio.month - 1 + meses
    anio = fecha_inicio.year + mes_base // 12
    mes = mes_base % 12 + 1
    dia = min(fecha_inicio.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)
