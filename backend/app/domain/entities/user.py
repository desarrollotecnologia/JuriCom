"""Entidad User (capa de dominio, pura).



Las entidades de dominio NO conocen ni a SQLAlchemy ni a FastAPI.

Son objetos planos con reglas de negocio.

"""



from dataclasses import dataclass

from datetime import datetime

from typing import TYPE_CHECKING, Optional



from app.domain.value_objects.roles import Role



if TYPE_CHECKING:

    from app.domain.entities.solicitud_gestion import SolicitudGestion





@dataclass

class User:

    username: str

    password_hash: str

    role: Role

    email: str = ""

    lider_catalog_id: str = ""

    id: Optional[int] = None

    is_active: bool = True

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    created_by_id: Optional[int] = None



    def is_admin(self) -> bool:

        return self.role == Role.ADMIN



    def is_juridica(self) -> bool:

        return self.role == Role.JURIDICA



    def is_compras(self) -> bool:

        return self.role == Role.COMPRAS



    def is_solicitante(self) -> bool:

        return self.role == Role.SOLICITANTE



    def is_anticipos(self) -> bool:

        return self.role == Role.ANTICIPOS



    def is_lider_aprobador(self) -> bool:

        return self.role == Role.LIDER_APROBADOR



    def puede_crear_solicitudes_gestion(self) -> bool:
        return self.is_admin() or self.is_compras() or self.is_solicitante() or self.is_anticipos()

    def ve_solo_propias_solicitudes_gestion(self) -> bool:
        return (
            (self.is_compras() or self.is_solicitante() or self.is_anticipos())
            and not self.is_admin()
        )

    def puede_gestionar_panel_compras(self) -> bool:
        return self.is_admin() or self.is_compras()

    def puede_operar_anticipos(self) -> bool:
        return self.is_admin() or self.is_anticipos()



    def puede_aprobar_solicitudes_gestion(self) -> bool:
        return self.is_admin() or self.is_lider_aprobador()



    def puede_aprobar_anticipo_solicitud(self) -> bool:
        return self.is_admin() or self.is_lider_aprobador()



    def lider_id_catalogo(self) -> str:

        return (self.lider_catalog_id or "").strip()



    def solicitud_asignada_a_lider(self, solicitud: "SolicitudGestion") -> bool:

        from app.domain.value_objects.estado_solicitud_gestion import (

            EstadoSolicitudGestion,

            normalizar_estado,

        )



        lid = self.lider_id_catalogo()

        if not lid:

            return False



        estado = normalizar_estado(solicitud.estado)

        if estado in (

            EstadoSolicitudGestion.SOLICITUD,

            EstadoSolicitudGestion.REGISTRADA,

            EstadoSolicitudGestion.APROBACION_LIDER_AREA,

            EstadoSolicitudGestion.PRIMERA_APROBACION,

        ):

            return (solicitud.lider_area_id or "").strip() == lid

        if estado == EstadoSolicitudGestion.EN_APROBACION:

            return (solicitud.lider_segunda_aprobacion_id or "").strip() == lid

        if estado == EstadoSolicitudGestion.APROBACION_ANTICIPO:

            return (solicitud.lider_anticipo_id or "").strip() == lid

        return False



    def can_manage_users(self) -> bool:

        """Sólo el administrador puede gestionar usuarios."""

        return self.is_admin()


