"""Registra observación en trazabilidad y cierra la gestión del anticipo."""



from app.application.interfaces.file_storage import FileStorage

from app.application.interfaces.solicitud_gestion_repository import (

    SolicitudGestionRepository,

)

from app.application.services.solicitud_gestion_notificaciones import (
    NotificadorSolicitudGestion,
)

from app.application.use_cases.solicitudes_gestion.agregar_observacion_solicitud import (

    AgregarObservacionSolicitud,

)

from app.application.use_cases.solicitudes_gestion.avanzar_flujo_post_oc import (
    avanzar_a_items_en_camino,
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





class GestionarAnticipoSolicitud:

    def __init__(

        self,

        solicitudes: SolicitudGestionRepository,

        storage: FileStorage | None = None,

        notificador: NotificadorSolicitudGestion | None = None,

    ) -> None:

        self._solicitudes = solicitudes

        self._storage = storage

        self._notificador = notificador



    def execute(

        self,

        actor: User,

        solicitud_id: int,

        *,

        nueva_observacion: str = "",

        nueva_observacion_texto: str = "",

        archivos_observacion: list[ArchivoEntradaSolicitud] | None = None,

    ) -> SolicitudGestion:

        if not actor.puede_operar_anticipos():

            raise UnauthorizedError("Sólo Anticipos o Admin pueden gestionar anticipos.")



        solicitud = self._solicitudes.get_by_id(solicitud_id)

        if solicitud is None:

            raise ContratoNotFoundError(f"No existe la solicitud {solicitud_id}.")



        if normalizar_estado(solicitud.estado) != EstadoSolicitudGestion.GESTION_ANTICIPO:

            raise ValueError("La solicitud no está en gestión de anticipo.")



        if (

            solicitud.gestor_anticipo_id

            and solicitud.gestor_anticipo_id != actor.id

            and not actor.is_admin()

            and not actor.is_anticipos()

        ):

            raise UnauthorizedError("Sólo el gestor asignado puede cerrar este anticipo.")



        nota_texto = (nueva_observacion_texto or "").strip()

        nota_html = (nueva_observacion or "").strip()

        adjuntos = archivos_observacion or []



        if nota_texto or nota_html or adjuntos:

            AgregarObservacionSolicitud(self._solicitudes, self._storage).execute(

                actor,

                solicitud_id,

                contenido=nota_html,

                contenido_texto=nota_texto,

                contexto_rol="gestor",

                archivos=adjuntos,

            )



        solicitud.gestor_id = actor.id

        comentario_hist = "Anticipo gestionado — solicitud continúa en Tramitada OC"

        if nota_texto:

            comentario_hist = f"Anticipo gestionado — {nota_texto[:500]}"

        self._solicitudes.update(solicitud)

        refreshed = avanzar_a_items_en_camino(
            self._solicitudes,
            solicitud_id,
            actor.id,
            comentario_tramitada=comentario_hist,
        )

        resultado = refreshed or solicitud
        if self._notificador:
            self._notificador.notificar_anticipo_gestionado(resultado, actor)
        return resultado

