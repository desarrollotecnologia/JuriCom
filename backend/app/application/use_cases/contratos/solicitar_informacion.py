"""Caso de uso: Jurídica solicita información faltante a Compras.

Reglas:
- Sólo Jurídica o Admin pueden solicitar información.
- El mensaje (qué falta) es obligatorio.
- Puede adjuntar fotos u otros archivos (opcional).
- Compras/supervisor tiene un plazo en días hábiles para responder.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.file_storage import FileStorage
from app.domain.entities.contrato import ArchivoAdjunto, TipoArchivo
from app.domain.entities.solicitud_informacion import (
    SolicitudInformacion,
    calcular_fecha_limite_respuesta,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError


@dataclass
class ArchivoSolicitudInfo:
    nombre_original: str
    mime_type: str
    contenido: bytes


class SolicitarInformacion:
    def __init__(
        self, contratos: ContratoRepository, storage: Optional[FileStorage] = None
    ) -> None:
        self._contratos = contratos
        self._storage = storage

    def execute(
        self,
        actor: User,
        contrato_id: int,
        mensaje: str,
        archivos: Optional[list[ArchivoSolicitudInfo]] = None,
    ) -> SolicitudInformacion:
        if not (actor.is_admin() or actor.is_juridica()):
            raise UnauthorizedError(
                "Sólo Jurídica o el Administrador pueden solicitar información."
            )

        contrato = self._contratos.get_by_id(contrato_id)
        if contrato is None:
            raise ContratoNotFoundError(f"No existe el contrato {contrato_id}.")

        mensaje_limpio = (mensaje or "").strip()
        if not mensaje_limpio:
            raise ValueError("Debes describir qué información falta.")

        solicitud = SolicitudInformacion(
            contrato_id=contrato_id,
            solicitado_por_id=actor.id,
            mensaje=mensaje_limpio,
            fecha_limite_respuesta=calcular_fecha_limite_respuesta(date.today()),
        )
        solicitud = self._contratos.crear_solicitud_informacion(solicitud)

        for entrada in archivos or []:
            self._guardar_archivo(contrato_id, solicitud.id, actor, entrada)

        if archivos:
            recargada = self._contratos.get_solicitud_informacion(solicitud.id)
            if recargada is not None:
                return recargada
        return solicitud

    def _guardar_archivo(
        self,
        contrato_id: int,
        solicitud_id: int,
        actor: User,
        entrada: ArchivoSolicitudInfo,
    ) -> None:
        if self._storage is None:
            raise ValueError("No hay almacenamiento configurado para adjuntos.")
        stored = self._storage.save(
            contenido=entrada.contenido,
            nombre_original=entrada.nombre_original,
            mime_type=entrada.mime_type,
            subcarpeta="contratos",
        )
        self._contratos.add_archivo(
            ArchivoAdjunto(
                tipo=TipoArchivo.SOLICITUD_INFORMACION,
                nombre_original=stored.nombre_original,
                ruta_almacenamiento=stored.ruta,
                mime_type=stored.mime_type,
                tamano_bytes=stored.tamano_bytes,
                contrato_id=contrato_id,
                subido_por_id=actor.id,
                solicitud_informacion_id=solicitud_id,
            )
        )
