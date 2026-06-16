"""Etiquetas de rol para trazabilidad de observaciones."""

from app.domain.entities.user import User
from app.domain.value_objects.roles import Role

ROLE_LABEL: dict[Role, str] = {
    Role.ADMIN: "Administrador",
    Role.COMPRAS: "Compras",
    Role.JURIDICA: "Jurídica",
}


def etiqueta_rol_usuario(user: User, *, contexto: str = "default") -> str:
    if contexto == "gestor":
        return "Gestor"
    if contexto == "solicitante":
        return "Usuario Solicitante"
    if contexto == "aprobador":
        return "Líder Aprobador"
    if contexto == "aprobador_primera":
        return "Líder Aprobador (Primera Aprobación)"
    if contexto == "aprobador_segunda":
        return "Líder Aprobador (Segunda Aprobación)"
    return ROLE_LABEL.get(user.role, user.role.value)
