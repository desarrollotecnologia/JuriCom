"""Caso de uso: el supervisor responde una solicitud de información faltante.

Reglas:
- Sólo puede responder el supervisor asignado al contrato (o el Admin).
- La respuesta de texto es obligatoria; los archivos son opcionales.
- Los adjuntos quedan como documentos del contrato (tipo RESPUESTA_INFORMACION).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
from app.domain.entities.contrato import ArchivoAdjunto, TipoArchivo
from app.domain.entities.solicitud_informacion import (
    ESTADO_RESPONDIDA,
    SolicitudInformacion,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError


@dataclass
class ArchivoRespuesta:
    nombre_original: str
    mime_type: str
    contenido: bytes


class ResponderInformacion:
    def __init__(self, contratos: ContratoRepository, storage: FileStorage) -> None:
        self._contratos = contratos
        self._storage = storage

    def execute(
        self,
        actor: User,
        contrato_id: int,
        solicitud_id: int,
        respuesta: str,
        archivos: Optional[list[ArchivoRespuesta]] = None,
    ) -> SolicitudInformacion:
        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")

        es_supervisor = actor.is_solicitante() and contrato.supervisor_id == actor.id
        if not (actor.is_admin() or es_supervisor):
            raise UnauthorizedError(
                "Sólo el supervisor asignado a este contrato (o el "
                "Administrador) puede responder la solicitud."
            )

        solicitud = self._contratos.get_solicitud_informacion(solicitud_id)
        if solicitud is None or solicitud.contrato_id != contrato_id:
            raise ContratoNotFoundError("No existe la solicitud de información.")
        if not solicitud.pendiente:
            raise ValueError("Esta solicitud de información ya fue respondida.")

        respuesta_limpia = (respuesta or "").strip()
        if not respuesta_limpia:
            raise ValueError("Debes escribir la respuesta con la información solicitada.")

        for entrada in archivos or []:
            self._guardar_archivo(contrato_id, solicitud_id, actor, entrada)

        solicitud.respuesta = respuesta_limpia
        solicitud.estado = ESTADO_RESPONDIDA
        solicitud.respondido_por_id = actor.id
        solicitud.respondido_at = datetime.now()
        return self._contratos.actualizar_solicitud_informacion(solicitud)

    def _guardar_archivo(
        self, contrato_id: int, solicitud_id: int, actor: User, entrada: ArchivoRespuesta
    ) -> ArchivoAdjunto:
        stored = self._storage.save(
            contenido=entrada.contenido,
            nombre_original=entrada.nombre_original,
            mime_type=entrada.mime_type,
            subcarpeta="contratos",
        )
        archivo = ArchivoAdjunto(
            tipo=TipoArchivo.RESPUESTA_INFORMACION,
            nombre_original=stored.nombre_original,
            ruta_almacenamiento=stored.ruta,
            mime_type=stored.mime_type,
            tamano_bytes=stored.tamano_bytes,
            contrato_id=contrato_id,
            subido_por_id=actor.id,
            solicitud_informacion_id=solicitud_id,
        )
        return self._contratos.add_archivo(archivo)
