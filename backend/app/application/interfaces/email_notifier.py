"""Interfaz para envío de notificaciones por correo.

Permite cambiar la implementación (SMTP, SendGrid, log only, etc.)
sin tocar los casos de uso.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    asunto: str
    destinatarios: list[str]
    cuerpo_html: str
    cuerpo_texto: str = ""


class EmailNotifier(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> None: ...

    @property
    @abstractmethod
    def disponible(self) -> bool: ...
