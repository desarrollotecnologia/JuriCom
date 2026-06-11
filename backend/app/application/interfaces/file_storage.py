"""Interfaz para almacenamiento de archivos.

Permite cambiar entre disco local, S3, etc., sin tocar casos de uso.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredFile:
    ruta: str
    nombre_original: str
    mime_type: str
    tamano_bytes: int


class FileStorage(ABC):
    @abstractmethod
    def save(
        self,
        contenido: bytes,
        nombre_original: str,
        mime_type: str,
        subcarpeta: str,
    ) -> StoredFile: ...

    @abstractmethod
    def delete(self, ruta: str) -> None: ...
