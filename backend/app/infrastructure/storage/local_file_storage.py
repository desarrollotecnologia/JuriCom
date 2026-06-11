"""Almacenamiento local de archivos en disco.

Si en el futuro pasan a S3/Azure Blob, basta con escribir otra clase
que implemente la interfaz `FileStorage`.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

from app.application.interfaces.file_storage import FileStorage, StoredFile
from app.infrastructure.config import settings


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or settings.upload_dir_path
        self._base.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        contenido: bytes,
        nombre_original: str,
        mime_type: str,
        subcarpeta: str,
    ) -> StoredFile:
        carpeta = self._base / subcarpeta / datetime.utcnow().strftime("%Y/%m")
        carpeta.mkdir(parents=True, exist_ok=True)

        extension = Path(nombre_original).suffix.lower()
        nombre_seguro = f"{uuid.uuid4().hex}{extension}"
        ruta_completa = carpeta / nombre_seguro

        with open(ruta_completa, "wb") as f:
            f.write(contenido)

        # Guardamos ruta relativa al base_dir (más portable).
        ruta_relativa = str(ruta_completa.relative_to(self._base)).replace("\\", "/")
        return StoredFile(
            ruta=ruta_relativa,
            nombre_original=nombre_original,
            mime_type=mime_type,
            tamano_bytes=len(contenido),
        )

    def delete(self, ruta: str) -> None:
        ruta_completa = self._base / ruta
        if ruta_completa.exists():
            os.remove(ruta_completa)
