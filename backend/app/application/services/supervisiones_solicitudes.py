"""Supervisión de solicitudes: usuarios que pueden ver (y trazar) las solicitudes
creadas por otros.

La clave es el correo del "visor" y el valor son los correos de los solicitantes
cuyas solicitudes puede consultar (listado + detalle + trazabilidad), sin poder
editarlas (solo el creador edita).

ponytail: mapa fijo por correo (config Colbeef, igual que lideres_colbeef). Techo:
si crece mucho o cambia seguido, moverlo a una tabla/relación en BD. Upgrade:
modelo de "equipo/área" con supervisores.
"""

_SUPERVISIONES: dict[str, tuple[str, ...]] = {
    "mantenimiento@colbeef.com": (
        "planeador.colbeef@soatsas.com",
        "aux.mantenimiento@colbeef.com",
    ),
}


def emails_supervisados(email: str) -> set[str]:
    """Correos cuyas solicitudes puede ver el `email` dado (en minúsculas)."""
    return {e.strip().lower() for e in _SUPERVISIONES.get((email or "").strip().lower(), ())}


# Especialistas de mantenimiento que integran el comité técnico: ven (sin votar)
# todas las SRV que están en mesa técnica, con sus cotizaciones. PMO = rol Proyectos,
# que ya participa del comité por su rol.
_MIEMBROS_COMITE_TECNICO: frozenset[str] = frozenset(
    {
        "mantenimiento@colbeef.com",
        "aux.mantenimiento@colbeef.com",
        "planeador.colbeef@soatsas.com",
    }
)


def es_miembro_comite_tecnico(email: str) -> bool:
    return (email or "").strip().lower() in _MIEMBROS_COMITE_TECNICO
