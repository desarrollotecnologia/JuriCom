"""Casos de uso para el cierre del contrato: informe final y acta de liquidación.

Reglas de negocio (parametrizadas por `umbral_acta`, por defecto 15.000.000):

- El supervisor asignado (o el Admin) entrega el **informe final** de un contrato
  activo y aprobado.
- Contratos con valor <= umbral: el informe final es suficiente y el contrato
  pasa a **Cierre en contabilidad** (pago final Contabilidad → Tesorería → Completado).
- Contratos con valor > umbral: además se requiere el **acta de liquidación**, que
  elabora/carga **Jurídica**. Al entregar el informe el contrato NO avanza al cierre:
  queda esperando que Jurídica cargue el acta (que sí lo manda a Cierre en contabilidad).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
from app.domain.entities.contrato import ArchivoAdjunto, Contrato, TipoArchivo
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato

UMBRAL_ACTA_DEFAULT = Decimal("15000000")

# Estados donde el contrato ya salió de ACTIVO hacia el cierre/finalización: no se
# puede volver a entregar informe/acta.
_ESTADOS_CIERRE_O_FINAL = {
    EstadoContrato.CIERRE_CONTABILIDAD,
    EstadoContrato.CIERRE_TESORERIA,
    EstadoContrato.COMPLETADO,
    EstadoContrato.FINALIZADO,
}


@dataclass
class ArchivoFinalizacion:
    tipo: TipoArchivo
    nombre_original: str
    mime_type: str
    contenido: bytes


def _guardar_archivo(
    contratos: ContratoRepository,
    storage: FileStorage,
    contrato: Contrato,
    contrato_id: int,
    actor: User,
    entrada: ArchivoFinalizacion,
) -> ArchivoAdjunto:
    stored = storage.save(
        contenido=entrada.contenido,
        nombre_original=entrada.nombre_original,
        mime_type=entrada.mime_type,
        subcarpeta="contratos",
    )
    archivo = ArchivoAdjunto(
        tipo=entrada.tipo,
        nombre_original=stored.nombre_original,
        ruta_almacenamiento=stored.ruta,
        mime_type=stored.mime_type,
        tamano_bytes=stored.tamano_bytes,
        contrato_id=contrato_id,
        subido_por_id=actor.id,
    )
    guardado = contratos.add_archivo(archivo)
    # Reflejar el archivo en la entidad para que la respuesta inmediata sea correcta.
    try:
        contrato.archivos.append(guardado)
    except Exception:
        pass
    return guardado


class FinalizarContratoCompras:
    """El supervisor entrega el informe final (y, si aplica, finaliza el contrato)."""

    def __init__(
        self,
        contratos: ContratoRepository,
        storage: FileStorage,
        umbral_acta: Decimal = UMBRAL_ACTA_DEFAULT,
    ) -> None:
        self._contratos = contratos
        self._storage = storage
        self._umbral_acta = Decimal(umbral_acta)

    def execute(
        self,
        actor: User,
        contrato_id: int,
        informe_final: Optional[ArchivoFinalizacion],
    ) -> Contrato:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")

        es_supervisor_asignado = (
            actor.id is not None and actor.id == getattr(contrato, "supervisor_id", None)
        )
        if not (actor.is_admin() or es_supervisor_asignado):
            raise UnauthorizedError(
                "Sólo el supervisor asignado a este contrato (o el Administrador) "
                "puede entregar el informe final."
            )
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )
        if contrato.estado in _ESTADOS_CIERRE_O_FINAL:
            raise ValueError("El contrato ya está en cierre o finalizado.")
        if contrato.estado != EstadoContrato.ACTIVO:
            raise ValueError("Sólo se puede finalizar un contrato que esté activo.")
        if informe_final is None:
            raise ValueError("Debes adjuntar el informe final.")

        _guardar_archivo(
            self._contratos, self._storage, contrato, contrato_id, actor, informe_final
        )

        # Contratos > umbral: el acta la elabora Jurídica. El contrato NO avanza al
        # cierre aquí; queda esperando el acta de liquidación.
        if Decimal(contrato.valor) > self._umbral_acta:
            return self._contratos.update(contrato)

        # Ya no finaliza directo: pasa al cierre con Contabilidad → Tesorería.
        contrato.estado = EstadoContrato.CIERRE_CONTABILIDAD
        return self._contratos.update(contrato)


class CargarActaLiquidacion:
    """Jurídica carga el acta y manda el contrato al cierre contable (> umbral)."""

    def __init__(
        self,
        contratos: ContratoRepository,
        storage: FileStorage,
        umbral_acta: Decimal = UMBRAL_ACTA_DEFAULT,
    ) -> None:
        self._contratos = contratos
        self._storage = storage
        self._umbral_acta = Decimal(umbral_acta)

    def execute(
        self,
        actor: User,
        contrato_id: int,
        acta_liquidacion: Optional[ArchivoFinalizacion],
    ) -> Contrato:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")

        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica (o el Administrador) puede cargar el acta de liquidación."
            )
        if contrato.estado in _ESTADOS_CIERRE_O_FINAL:
            raise ValueError("El contrato ya está en cierre o finalizado.")
        if contrato.estado != EstadoContrato.ACTIVO:
            raise ValueError("Sólo se puede liquidar un contrato que esté activo.")
        if Decimal(contrato.valor) <= self._umbral_acta:
            raise ValueError(
                "Este contrato no requiere acta de liquidación (su valor no supera el umbral)."
            )
        if not contrato.tiene_informe_final():
            raise ValueError(
                "Primero el supervisor debe entregar el informe final antes de elaborar el acta."
            )
        if acta_liquidacion is None:
            raise ValueError("Debes adjuntar el acta de liquidación.")

        _guardar_archivo(
            self._contratos, self._storage, contrato, contrato_id, actor, acta_liquidacion
        )
        contrato.estado = EstadoContrato.CIERRE_CONTABILIDAD
        return self._contratos.update(contrato)
