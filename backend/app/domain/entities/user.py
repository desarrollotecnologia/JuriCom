"""Entidad User (capa de dominio, pura).



Las entidades de dominio NO conocen ni a SQLAlchemy ni a FastAPI.

Son objetos planos con reglas de negocio.

"""



from dataclasses import dataclass, field

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

    nombre: str = ""

    email: str = ""

    lider_catalog_id: str = ""

    # Roles adicionales (multi-rol). `role` es el rol principal; estos se suman.
    extra_roles: list[Role] = field(default_factory=list)

    id: Optional[int] = None

    is_active: bool = True

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    created_by_id: Optional[int] = None



    def roles(self) -> list[Role]:
        """Todos los roles activos del usuario (principal + adicionales, sin duplicar)."""
        vistos: list[Role] = []
        for r in [self.role, *self.extra_roles]:
            if r not in vistos:
                vistos.append(r)
        return vistos

    def tiene_rol(self, rol: Role) -> bool:
        return rol == self.role or rol in self.extra_roles

    def is_admin(self) -> bool:

        return self.tiene_rol(Role.ADMIN)



    def is_juridica(self) -> bool:

        return self.tiene_rol(Role.JURIDICA)



    def is_compras(self) -> bool:

        return self.tiene_rol(Role.COMPRAS)



    def is_solicitante(self) -> bool:

        return self.tiene_rol(Role.SOLICITANTE)



    def is_anticipos(self) -> bool:

        return self.tiene_rol(Role.ANTICIPOS)



    def is_lider_aprobador(self) -> bool:

        return self.tiene_rol(Role.LIDER_APROBADOR)



    def is_proyectos(self) -> bool:

        return self.tiene_rol(Role.PROYECTOS)



    def is_contabilidad(self) -> bool:

        return self.tiene_rol(Role.CONTABILIDAD)



    def is_tesoreria(self) -> bool:

        return self.tiene_rol(Role.TESORERIA)



    def puede_crear_solicitudes_gestion(self) -> bool:
        return (
            self.is_admin()
            or self.is_compras()
            or self.is_solicitante()
            or self.is_anticipos()
            or self.is_proyectos()
        )

    def ve_solo_propias_solicitudes_gestion(self) -> bool:
        return (
            (
                self.is_compras()
                or self.is_solicitante()
                or self.is_anticipos()
                or self.is_proyectos()
            )
            and not self.is_admin()
        )

    def puede_gestionar_panel_compras(self) -> bool:
        return self.is_admin() or self.is_compras()

    def puede_cotizar_proyectos(self) -> bool:
        """Rol proyectos: cotiza SRV que requieren comité técnico."""
        return self.is_admin() or self.is_proyectos()

    def puede_operar_anticipos(self) -> bool:
        return self.is_admin() or self.is_anticipos()

    def puede_gestionar_anticipo_contabilidad(self) -> bool:
        """Rol contabilidad: gestiona el anticipo del contrato antes de tesorería."""
        return self.is_admin() or self.is_contabilidad()

    def puede_gestionar_anticipo_tesoreria(self) -> bool:
        """Rol tesorería: confirma el pago del anticipo del contrato."""
        return self.is_admin() or self.is_tesoreria()



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


