"""Interfaz para envío de notificaciones por correo.

Permite cambiar la implementación (SMTP, SendGrid, log only, etc.)
sin tocar los casos de uso.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EmailAttachment:
    """Archivo adjunto a un correo (contenido en memoria)."""

    nombre: str
    contenido: bytes
    mime_type: str = "application/octet-stream"


@dataclass
class EmailMessage:
    asunto: str
    destinatarios: list[str]
    cuerpo_html: str
    cuerpo_texto: str = ""
    adjuntos: list[EmailAttachment] = field(default_factory=list)


class EmailNotifier(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> None: ...

    @property
    @abstractmethod
    def disponible(self) -> bool: ...
