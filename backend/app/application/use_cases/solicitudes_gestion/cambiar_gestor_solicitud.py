"""Reasigna el gestor (usuario de Compras) de una solicitud abierta en el panel."""

from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.interfaces.user_repository import UserRepository
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    ETAPAS_PANEL_GESTION,
    normalizar_estado,
)
from app.domain.value_objects.roles import Role


class CambiarGestorSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        users: UserRepository,
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._users = users
        self._notificador = notificador

    def gestores_disponibles(self, actor: User) -> list[User]:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden ver los gestores.")
        return sorted(
            (u for u in self._users.list_all() if u.is_active and u.tiene_rol(Role.COMPRAS)),
            key=lambda u: (u.username or "").lower(),
        )

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        nuevo_gestor_id: int,
        comentario: str = "",
    ) -> SolicitudGestion:
        if not (actor.is_admin() or actor.is_compras()):
            raise UnauthorizedError("Sólo Compras o Admin pueden cambiar el gestor.")

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        estado = normalizar_estado(solicitud.estado)
        if estado not in ETAPAS_PANEL_GESTION:
            raise ValueError("Sólo se puede cambiar el gestor de solicitudes abiertas en el panel.")
        # Sin gestor, cualquiera de Compras puede asignarla (equivale a tomarla).
        if solicitud.gestor_id and not actor.is_admin() and solicitud.gestor_id != actor.id:
            raise UnauthorizedError("Sólo el gestor asignado o un Admin puede cambiar el gestor.")

        nuevo = self._users.get_by_id(int(nuevo_gestor_id))
        if nuevo is None or not nuevo.is_active or not nuevo.tiene_rol(Role.COMPRAS):
            raise ValueError("El nuevo gestor debe ser un usuario activo de Compras.")
        if nuevo.id == solicitud.gestor_id:
            raise ValueError("Ese usuario ya es el gestor de la solicitud.")

        anterior = (solicitud.gestor_username or "").strip() or "sin gestor"
        comentario = (comentario or "").strip()
        solicitud.gestor_id = nuevo.id
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            estado,
            usuario_id=actor.id,
            comentario=(
                f"Gestor cambiado de {anterior} a {nuevo.username} por {actor.username}"
                + (f": {comentario}" if comentario else "")
            ),
        )
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador:
            self._notificador.notificar_cambio_gestor(resultado, actor, nuevo, comentario)
        return resultado
