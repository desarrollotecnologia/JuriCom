"""Confirma la visita programada (estado previo a cotizar) y avanza el flujo.

Aplica a servicios que el solicitante marcó como "requiere visita". La visita la
agenda Compras (flujo normal) o Proyectos (comité técnico): datos del proveedor
manuales + fecha + hora + una observación opcional. Al confirmar, la solicitud
pasa a la etapa de cotización correspondiente.
"""

from app.application.interfaces.file_storage import FileStorage
from app.application.interfaces.solicitud_gestion_repository import (
    SolicitudGestionRepository,
)
from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (
    AgregarObservacionSolicitud,
)
from app.application.use_cases.solicitudes_gestion.enviar_cotizacion_solicitud import (
    _parse_visitas_programadas,
    _validar_visitas_servicios,
)
from app.application.use_cases.solicitudes_gestion.registrar_solicitud_compra import (
    ArchivoEntradaSolicitud,
)
from app.domain.entities.user import User
from app.domain.exceptions import ContratoNotFoundError, UnauthorizedError
from app.domain.value_objects.estado_solicitud_gestion import (
    EstadoSolicitudGestion,
    normalizar_estado,
)


class GuardarGestionServiciosSolicitud:
    def __init__(
        self,
        solicitudes: SolicitudGestionRepository,
        storage: FileStorage,
    ) -> None:
        self._solicitudes = solicitudes
        self._storage = storage

    def execute(
        self,
        actor: User,
        solicitud_id: int,
        *,
        nueva_observacion: str = "",
        nueva_observacion_texto: str = "",
        visitas_json: str = "",
        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,
    ):
        es_proyectos = actor.puede_cotizar_proyectos()
        if not (actor.is_admin() or actor.is_compras() or es_proyectos):
            raise UnauthorizedError(
                "Sólo Compras, Proyectos o Admin pueden programar la visita."
            )

        solicitud = self._solicitudes.get_by_id(solicitud_id)
        if solicitud is None:
            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")

        from app.domain.value_objects.tipo_solicitud_gestion import es_flujo_servicios

        if not es_flujo_servicios(solicitud.tipo):
            raise ValueError("Esta acción solo aplica a solicitudes de servicios.")

        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.PROGRAMACION_VISITA:
            raise ValueError("La solicitud debe estar en estado Programar visita.")

        es_comite = bool(getattr(solicitud, "requiere_comite_tecnico", False))
        # Comité: la 1.ª visita la agenda Proyectos (antes de su cotización); la 2.ª
        # la agenda Compras (tras recibir las cotizaciones de Proyectos). Flujo normal:
        # siempre la agenda Compras.
        visita_de_proyectos = es_comite and not bool(
            getattr(solicitud, "visita_proyectos_hecha", False)
        )
        if visita_de_proyectos:
            if not (actor.is_admin() or es_proyectos):
                raise UnauthorizedError("Esta visita la agenda Proyectos.")
        else:
            if not (actor.is_admin() or actor.is_compras()):
                raise UnauthorizedError("Esta visita la agenda Compras.")
            if (
                solicitud.gestor_id
                and solicitud.gestor_id != actor.id
                and not actor.is_admin()
            ):
                raise UnauthorizedError("Sólo el gestor asignado puede agendar la visita.")

        visitas = _parse_visitas_programadas(visitas_json)
        if not visitas:
            raise ValueError(
                "Registra al menos una visita con proveedor y fecha."
            )
        _validar_visitas_servicios(solicitud, visitas)
        # Deja constancia de quién y con qué rol programó la visita.
        rol_actual = "proyectos" if visita_de_proyectos else "compras"
        for visita in visitas:
            visita.programador_visita = actor.username or ""
            visita.rol_programador = rol_actual
        nuevas = len(visitas)
        # Conserva las visitas agendadas por el otro rol (p. ej. las de Proyectos
        # cuando Compras agenda las suyas en el comité).
        previas_otro_rol = [
            v
            for v in (getattr(solicitud, "visitas_programadas", None) or [])
            if (getattr(v, "rol_programador", "") or "") != rol_actual
        ]
        visitas = previas_otro_rol + visitas

        nota_texto = (nueva_observacion_texto or "").strip()
        nota_html = (nueva_observacion or "").strip()
        adjuntos_obs = archivos_observacion or []
        if nota_texto or nota_html or adjuntos_obs:
            if not nota_texto and not nota_html and adjuntos_obs:
                nota_html = "<p>Archivos adjuntos.</p>"
                nota_texto = "Archivos adjuntos."
            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(
                actor,
                solicitud_id,
                contenido=nota_html,
                contenido_texto=nota_texto,
                contexto_rol="proyectos" if es_comite else "gestor",
                archivos=adjuntos_obs,
            )

        self._solicitudes.replace_visitas_programadas(solicitud_id, visitas)

        if visita_de_proyectos:
            destino = EstadoSolicitudGestion.COTIZACION_PROYECTOS
            solicitud.visita_proyectos_hecha = True
        else:
            destino = EstadoSolicitudGestion.COTIZACION
            if not solicitud.gestor_id:
                solicitud.gestor_id = actor.id
        solicitud.estado = destino
        self._solicitudes.update(solicitud)

        etiqueta_rol = "Proyectos" if rol_actual == "proyectos" else "Compras"
        comentario = (
            f"Visita programada por {etiqueta_rol} ({nuevas} visita"
            f"{'s' if nuevas != 1 else ''}); pasa a {destino.label}."
        )
        self._solicitudes.registrar_historial(
            solicitud_id,
            destino,
            usuario_id=actor.id,
            comentario=comentario,
        )

        resultado = self._solicitudes.get_by_id(solicitud_id)
        if resultado is None:
            raise RuntimeError("No se pudo recuperar la solicitud actualizada.")
        return resultado
