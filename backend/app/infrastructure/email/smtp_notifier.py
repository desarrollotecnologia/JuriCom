"""Notificador SMTP con manejo robusto de SSL/TLS.

Estrategia de conexión:
1. Si `use_ssl=True` y puerto = 465 → SMTPS (SSL implícito).
2. Si la negociación SSL falla con WRONG_VERSION_NUMBER → reintento con
   contexto SSL permisivo (acepta TLS 1.0+, certs no verificados).
3. Si aún así falla → fallback a SMTP plano + STARTTLS en el mismo puerto
   (algunos servidores antiguos exponen 465 como STARTTLS opcional).

Añade cabeceras Message-ID, Date y Reply-To para reducir
clasificación como spam.
"""

import logging
import smtplib
import socket
import ssl
import uuid
from email.message import EmailMessage as MimeEmail
from email.utils import formataddr, formatdate, make_msgid

from app.application.interfaces.email_notifier import EmailMessage, EmailNotifier
from app.infrastructure.config import settings


logger = logging.getLogger(__name__)


def _permisive_ssl_context() -> ssl.SSLContext:
    """Contexto SSL flexible para servidores SMTP antiguos.

    No verifica certificado ni hostname — adecuado para entornos
    corporativos donde el servidor puede usar cert auto-firmado o
    una cadena de certificación incompleta.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    # Habilitar protocolos antiguos por si el servidor solo soporta TLS 1.0/1.1
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except (AttributeError, ValueError):
        pass
    return ctx


class SmtpEmailNotifier(EmailNotifier):
    def __init__(
        self,
        host: str = settings.SMTP_HOST,
        port: int = settings.SMTP_PORT,
        use_ssl: bool = settings.SMTP_USE_SSL,
        username: str = settings.SMTP_USERNAME,
        password: str = settings.SMTP_PASSWORD,
        from_email: str = settings.SMTP_FROM_EMAIL,
        from_name: str = settings.SMTP_FROM_NAME,
        timeout: int = 20,
    ) -> None:
        self._host = host
        self._port = port
        self._use_ssl = use_ssl
        self._username = username
        self._password = password
        self._from_email = from_email
        self._from_name = from_name
        self._timeout = timeout

    @property
    def disponible(self) -> bool:
        return bool(self._host and self._username and self._from_email)

    def send(self, message: EmailMessage) -> None:
        if not self.disponible:
            logger.warning("SMTP no configurado; se omite envío a %s", message.destinatarios)
            return
        if not message.destinatarios:
            logger.warning("No hay destinatarios para '%s'; se omite envío", message.asunto)
            return

        mime = self._build_mime(message)

        # Estrategia con fallback
        errors: list[str] = []
        for intento in self._estrategias():
            try:
                intento(mime, message.destinatarios)
                logger.info(
                    "Correo enviado a %s — asunto: %s",
                    ", ".join(message.destinatarios),
                    message.asunto,
                )
                return
            except (ssl.SSLError, smtplib.SMTPException, socket.error, OSError) as e:
                errors.append(f"{type(e).__name__}: {e}")
                logger.warning("Intento SMTP fallido (%s): %s", type(e).__name__, e)

        msg_errores = " | ".join(errors)
        logger.error(
            "Todos los intentos SMTP fallaron para '%s': %s",
            message.asunto,
            msg_errores,
        )
        raise RuntimeError(f"SMTP envío fallido: {msg_errores}")

    # ------- construcción de mensaje -------

    def _build_mime(self, message: EmailMessage) -> MimeEmail:
        mime = MimeEmail()
        mime["Subject"] = message.asunto
        mime["From"] = formataddr((self._from_name, self._from_email))
        mime["To"] = ", ".join(message.destinatarios)
        mime["Reply-To"] = self._from_email
        mime["Date"] = formatdate(localtime=True)
        mime["Message-ID"] = make_msgid(domain=self._domain_from_email())
        mime["X-Mailer"] = "JURICOM_BEEF v0.2"
        mime["MIME-Version"] = "1.0"

        if message.cuerpo_texto:
            mime.set_content(message.cuerpo_texto)
        else:
            mime.set_content(
                "Este correo requiere cliente con soporte HTML."
            )
        mime.add_alternative(message.cuerpo_html, subtype="html")
        return mime

    def _domain_from_email(self) -> str:
        if "@" in self._from_email:
            return self._from_email.split("@", 1)[1]
        return "localhost"

    # ------- estrategias de envío -------

    def _estrategias(self):
        if self._use_ssl:
            yield self._send_ssl_strict
            yield self._send_ssl_permissive
            yield self._send_starttls_fallback
        else:
            yield self._send_starttls
            yield self._send_plain

    def _send_ssl_strict(self, mime: MimeEmail, destinatarios: list[str]) -> None:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            self._host, self._port, context=ctx, timeout=self._timeout
        ) as smtp:
            smtp.login(self._username, self._password)
            smtp.send_message(mime, to_addrs=destinatarios)

    def _send_ssl_permissive(self, mime: MimeEmail, destinatarios: list[str]) -> None:
        ctx = _permisive_ssl_context()
        with smtplib.SMTP_SSL(
            self._host, self._port, context=ctx, timeout=self._timeout
        ) as smtp:
            smtp.login(self._username, self._password)
            smtp.send_message(mime, to_addrs=destinatarios)

    def _send_starttls_fallback(self, mime: MimeEmail, destinatarios: list[str]) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls(context=_permisive_ssl_context())
                smtp.ehlo()
            except smtplib.SMTPNotSupportedError:
                pass  # algunos servidores aceptan login sin TLS
            smtp.login(self._username, self._password)
            smtp.send_message(mime, to_addrs=destinatarios)

    def _send_starttls(self, mime: MimeEmail, destinatarios: list[str]) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            smtp.ehlo()
            smtp.starttls(context=_permisive_ssl_context())
            smtp.ehlo()
            smtp.login(self._username, self._password)
            smtp.send_message(mime, to_addrs=destinatarios)

    def _send_plain(self, mime: MimeEmail, destinatarios: list[str]) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            smtp.login(self._username, self._password)
            smtp.send_message(mime, to_addrs=destinatarios)
