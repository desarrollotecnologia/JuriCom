"""Etiquetas de rol para trazabilidad de observaciones."""

from app.domain.entities.user import User
from app.domain.value_objects.roles import Role

ROLE_LABEL: dict[Role, str] = {
    Role.ADMIN: "Administrador",
    Role.COMPRAS: "Compras",
    Role.JURIDICA: "Jurídica",
    Role.SOLICITANTE: "Usuario Solicitante",
    Role.ANTICIPOS: "Anticipos",
    Role.LIDER_APROBADOR: "Líder Aprobador",
    Role.PROYECTOS: "Proyectos",
    Role.CONTABILIDAD: "Contabilidad",
    Role.TESORERIA: "Tesorería",
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
    if contexto == "proyectos":
        return "Proyectos"
    if contexto == "comite":
        return "Comité técnico"
    if contexto == "juridica":
        return "Jurídica"
    if contexto == "contabilidad":
        return "Contabilidad"
    if contexto == "tesoreria":
        return "Tesorería"
    return ROLE_LABEL.get(user.role, user.role.value)
