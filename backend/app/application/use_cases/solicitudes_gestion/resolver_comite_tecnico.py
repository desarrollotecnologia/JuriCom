"""Comité técnico: aceptación (supervisor + proyectos) o recotización.

Tras la 2.ª aprobación de Diego, la SRV con comité técnico queda en estado
`Comité`. Se hace una reunión interna y tanto el supervisor (quien creó la SRV)
como Proyectos deben aceptar. Si ambos aceptan, vuelve a Compras para gestionar
el servicio. Si no hay acuerdo, se devuelve a Proyectos para recotizar.
"""

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.solicitud_gestion import SolicitudGestion
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


class ResolverComiteTecnico:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage | None = None,
        notificador: NotificadorSolicitudGestion | None = None,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage
        self._notificador = notificador

    def _get_en_comite(self, solicitud_id: int) -> SolicitudGestion:
        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")
        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.COMITE:
            raise ValueError("La solicitud no está en el comité técnico.")
        return solicitud

    @staticmethod
    def _roles_actor(actor: User, solicitud: SolicitudGestion) -> tuple[bool, bool]:
        es_supervisor = actor.id is not None and actor.id == solicitud.creado_por_id
        es_proyectos = actor.is_proyectos() or (
            actor.id is not None and actor.id == solicitud.proyectista_id
        )
        return es_supervisor, es_proyectos

    def _guardar_observacion(
        self,
        actor: User,
        solicitud_id: int,
        observacion: str,
        observacion_texto: str,
        archivos: list[ArchivoEntradaSolicitud] | None,
    ) -> None:
        nota_texto = (observacion_texto or "").strip()
        nota_html = (observacion or "").strip()
        adjuntos = archivos or []
        if not (nota_texto or nota_html or adjuntos):
            return
        from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
            AgregarObservacionSolicitud,
        )

        if not nota_texto and not nota_html:
            nota_html = "<p>Acta del comité técnico.</p>"
            nota_texto = "Acta del comité técnico."
        AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
            actor,
            solicitud_id,
            contenido=nota_html,
            contenido_texto=nota_texto,
            contexto_rol="comite",
            archivos=adjuntos,
        )

    def aceptar(
        self,
        actor: User,
        solicitud_id: int,
        *,
        observacion: str = "",
        observacion_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
    ) -> SolicitudGestion:
        solicitud = self._get_en_comite(solicitud_id)
        es_supervisor, es_proyectos = self._roles_actor(actor, solicitud)
        if not (es_supervisor or es_proyectos or actor.is_admin()):
            raise UnauthorizedError(
                "Sólo el supervisor de la SRV o Proyectos pueden aceptar el comité."
            )

        if es_supervisor:
            solicitud.comite_supervisor_ok = True
        if es_proyectos:
            solicitud.comite_proyectos_ok = True
        if actor.is_admin() and not es_supervisor and not es_proyectos:
            solicitud.comite_supervisor_ok = True
            solicitud.comite_proyectos_ok = True

        self._guardar_observacion(
            actor, solicitud_id, observacion, observacion_texto, archivos
        )

        ambos = solicitud.comite_supervisor_ok and solicitud.comite_proyectos_ok
        if ambos:
            # Tras el acuerdo de la mesa técnica, pasa a la 2.ª aprobación (Diego),
            # que elige la cotización ganadora y aprueba.
            solicitud.estado = EstadoSolicitudGestion.EN_APROBACION
            actualizada = self._solicitudes.update(solicitud)
            self._solicitudes.registrar_historial(
                solicitud_id,
                EstadoSolicitudGestion.EN_APROBACION,
                usuario_id=actor.id,
                comentario="Mesa técnica aprobada por supervisor y proyectos; pasa a 2.ª aprobación.",
            )
            resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
            if self._notificador:
                # La mesa técnica quedó aceptada; ahora avanza a la 2.ª aprobación
                # (Diego), a quien se notifica igual que al enviar cotizaciones.
                self._notificador.notificar_cotizacion_enviada(resultado, actor)
            return resultado

        actualizada = self._solicitudes.update(solicitud)
        quien = "supervisor" if es_supervisor else "proyectos"
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.COMITE,
            usuario_id=actor.id,
            comentario=f"Comité: {quien} aceptó. A la espera del otro participante.",
        )
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador:
            self._notificador.notificar_comite_aceptacion_parcial(resultado, actor)
        return resultado

    def recotizar(
        self,
        actor: User,
        solicitud_id: int,
        *,
        motivo: str = "",
        motivo_texto: str = "",
        archivos: list[ArchivoEntradaSolicitud] | None = None,
    ) -> SolicitudGestion:
        solicitud = self._get_en_comite(solicitud_id)
        es_supervisor, es_proyectos = self._roles_actor(actor, solicitud)
        if not (es_supervisor or es_proyectos or actor.is_admin()):
            raise UnauthorizedError(
                "Sólo el supervisor de la SRV o Proyectos pueden pedir recotización."
            )

        self._guardar_observacion(
            actor, solicitud_id, motivo, motivo_texto, archivos
        )

        solicitud.comite_supervisor_ok = False
        solicitud.comite_proyectos_ok = False
        solicitud.estado = EstadoSolicitudGestion.COTIZACION_PROYECTOS
        actualizada = self._solicitudes.update(solicitud)
        self._solicitudes.registrar_historial(
            solicitud_id,
            EstadoSolicitudGestion.COTIZACION_PROYECTOS,
            usuario_id=actor.id,
            comentario="Comité sin acuerdo: se devuelve a Proyectos para recotizar.",
        )
        resultado = self._solicitudes.get_by_id(solicitud_id) or actualizada
        if self._notificador:
            self._notificador.notificar_comite_recotizar(resultado, actor)
        return resultado
