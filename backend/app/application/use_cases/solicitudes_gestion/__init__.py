from .agregar_observacion_solicitud import AgregarObservacionSolicitud
from .enviar_cotizacion_solicitud import EnviarCotizacionSolicitud
from .gestionar_solicitud_panel import GestionarSolicitudPanel
from .get_solicitud_gestion import GetSolicitudGestion

from .listar_pendientes_aprobacion import ListarPendientesAprobacion

from .listar_solicitudes_gestion import ListarSolicitudesGestion

from .listar_solicitudes_panel import ListarSolicitudesPanelGestion

from .registrar_solicitud_compra import ArchivoEntradaSolicitud, RegistrarSolicitudCompra

from .marcar_entrega_solicitud import MarcarEntregaSolicitud
from .registrar_entrega_parcial_solicitud import RegistrarEntregaParcialSolicitud
from .registrar_tramite_oc_solicitud import RegistrarTramiteOcSolicitud
from .resolver_aprobacion_solicitud import ResolverAprobacionSolicitud
from .solicitar_recotizacion_solicitud import SolicitarRecotizacionSolicitud



__all__ = [

    "AgregarObservacionSolicitud",
    "ArchivoEntradaSolicitud",

    "EnviarCotizacionSolicitud",
    "GestionarSolicitudPanel",
    "GetSolicitudGestion",

    "ListarPendientesAprobacion",

    "ListarSolicitudesGestion",

    "ListarSolicitudesPanelGestion",

    "MarcarEntregaSolicitud",

    "RegistrarSolicitudCompra",

    "RegistrarEntregaParcialSolicitud",

    "RegistrarTramiteOcSolicitud",

    "ResolverAprobacionSolicitud",

    "SolicitarRecotizacionSolicitud",

]

