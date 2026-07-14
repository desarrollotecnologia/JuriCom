"""Caso de uso: Jurídica/Admin adjunta póliza o contrato firmado."""

from dataclasses import dataclass

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
from app.domain.entities.contrato import ArchivoAdjunto, TipoArchivo
from app.domain.entities.user import User
from app.domain.exceptions import (
    ContratoNotFoundError,
    InvalidFileError,
    UnauthorizedError,
)
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion


@dataclass
class ArchivoJuridicaEntrada:
    tipo: TipoArchivo
    nombre_original: str
    mime_type: str
    contenido: bytes


class AdjuntarArchivoJuridica:
    def __init__(self, contratos: ContratoRepository, storage: FileStorage) -> None:
        self._contratos = contratos
        self._storage = storage

    def execute(
        self,
        actor: User,
        contrato_id: int,
        entrada: ArchivoJuridicaEntrada,
    ) -> ArchivoAdjunto:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica o el Administrador pueden adjuntar póliza o borrador."
            )

        if entrada.tipo not in TipoArchivo.archivos_juridica():
            raise InvalidFileError(
                f"Tipo de archivo '{entrada.tipo.value}' no válido para esta operación."
            )

        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")
        if contrato.estado_aprobacion != EstadoAprobacion.APROBADO:
            raise UnauthorizedError(
                "Este contrato todavía no tiene aprobación de líder y gerencia."
            )

        stored = self._storage.save(
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
        return self._contratos.add_archivo(archivo)
