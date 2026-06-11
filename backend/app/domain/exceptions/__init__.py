"""Excepciones de dominio.

Estas excepciones representan errores de negocio (no técnicos).
La capa de presentación las traduce a códigos HTTP apropiados.
"""


class DomainError(Exception):
    """Excepción base del dominio."""


class InvalidCredentialsError(DomainError):
    """Usuario o contraseña incorrectos."""


class UserNotFoundError(DomainError):
    """No existe el usuario solicitado."""


class UserAlreadyExistsError(DomainError):
    """Ya existe un usuario con ese username."""


class UserInUseError(DomainError):
    """El usuario tiene contratos u otros registros asociados."""


class UnauthorizedError(DomainError):
    """El usuario no tiene permisos para esta acción."""


class InvalidRoleError(DomainError):
    """El rol indicado no existe."""


class ContratoNotFoundError(DomainError):
    """No existe el contrato solicitado."""


class InvalidFileError(DomainError):
    """Archivo inválido (tipo, tamaño, etc.)."""


class MissingRequiredFileError(DomainError):
    """Falta un archivo obligatorio."""


class InvalidContratoStateError(DomainError):
    """El contrato está en un estado que no permite esta operación."""
