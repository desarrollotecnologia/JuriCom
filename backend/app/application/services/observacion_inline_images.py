"""Extrae imágenes embebidas (data URI) del HTML de observaciones."""

import base64
import re
from dataclasses import dataclass

DATA_URI_IMG_PATTERN = re.compile(
    r'(<img\b[^>]*\bsrc=)(["\'])data:image/([^;\'"\s]+);base64,([^\'"\s]+)\2',
    re.IGNORECASE,
)

MIME_TO_EXT = {
    "png": "png",
    "jpeg": "jpg",
    "jpg": "jpg",
    "gif": "gif",
    "webp": "webp",
}


@dataclass(frozen=True)
class InlineImageExtract:
    mime_subtype: str
    contenido: bytes
    nombre: str


def _ext_for_subtype(subtype: str) -> str:
    key = (subtype or "png").lower()
    return MIME_TO_EXT.get(key, "png")


def extract_inline_images(html: str) -> tuple[str, list[InlineImageExtract]]:
    """Reemplaza data URIs por marcadores __PENDING_N__ y devuelve las imágenes decodificadas."""
    images: list[InlineImageExtract] = []

    def replacer(match: re.Match[str]) -> str:
        prefix, quote, subtype, b64data = match.groups()
        try:
            raw = base64.b64decode(b64data, validate=True)
        except (ValueError, TypeError):
            return match.group(0)
        if not raw:
            return match.group(0)

        idx = len(images)
        images.append(
            InlineImageExtract(
                mime_subtype=subtype,
                contenido=raw,
                nombre=f"imagen-inline-{idx + 1}.{_ext_for_subtype(subtype)}",
            )
        )
        return (
            f'{prefix}{quote}{quote} data-sg-archivo-id="__PENDING_{idx}__" '
            f'alt="Imagen embebida"'
        )

    processed = DATA_URI_IMG_PATTERN.sub(replacer, html or "")
    return processed, images


def apply_pending_archivo_ids(html: str, pending_to_id: dict[int, int]) -> str:
    result = html or ""
    for idx, archivo_id in pending_to_id.items():
        result = result.replace(f"__PENDING_{idx}__", str(archivo_id))
    return result
