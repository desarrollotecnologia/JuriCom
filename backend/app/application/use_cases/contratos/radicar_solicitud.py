"""Caso de uso: radicar una solicitud de contrato (rol Compras).

Encapsula las reglas de negocio:
- Sólo Compras o Admin pueden radicar.
- La compañía siempre es Colbeef.
- Deben adjuntarse los 3 archivos obligatorios.
- El archivo opcional (1 más) puede o no enviarse.
- La solicitud queda pendiente de aprobación del líder de proceso.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
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
    MissingRequiredFileError,
    UnauthorizedError,
)
from app.domain.value_objects.moneda import Moneda
from app.domain.value_objects.unidad_plazo import UnidadPlazo


@dataclass
class ArchivoEntrada:
    tipo: TipoArchivo
    nombre_original: str
    mime_type: str
    contenido: bytes


class RadicarSolicitud:
    def __init__(self, contratos: ContratoRepository, storage: FileStorage) -> None:
        self._contratos = contratos
        self._storage = storage

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

        return self._contratos.create(contrato)

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
