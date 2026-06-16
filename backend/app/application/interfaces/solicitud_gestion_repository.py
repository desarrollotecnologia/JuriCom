"""Puerto de persistencia para solicitudes de gestión."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.solicitud_gestion import (
    SolicitudGestion,
    SolicitudGestionArchivo,
    SolicitudGestionHistorialEstado,
    SolicitudGestionObservacion,
)
from app.domain.value_objects.estado_solicitud_gestion import EstadoSolicitudGestion
from app.domain.value_objects.tipo_solicitud_gestion import TipoSolicitudGestion


class SolicitudGestionRepository(ABC):
    @abstractmethod
    def create(self, solicitud: SolicitudGestion) -> SolicitudGestion:
        ...

    @abstractmethod
    def get_by_id(self, solicitud_id: int) -> Optional[SolicitudGestion]:
        ...

    @abstractmethod
    def list_all(
        self,
        *,
        creador_id: Optional[int] = None,
        excluir_creador_id: Optional[int] = None,
        tipo: Optional[TipoSolicitudGestion] = None,
        estados: Optional[list[EstadoSolicitudGestion]] = None,
        query: Optional[str] = None,
    ) -> list[SolicitudGestion]:
        ...

    @abstractmethod
    def update(self, solicitud: SolicitudGestion) -> SolicitudGestion:
        ...

    @abstractmethod
    def registrar_historial(
        self,
        solicitud_id: int,
        etapa: EstadoSolicitudGestion,
        *,
        usuario_id: Optional[int] = None,
        comentario: str = "",
    ) -> SolicitudGestionHistorialEstado:
        ...

    @abstractmethod
    def add_archivos(
        self,
        solicitud_id: int,
        archivos: list[SolicitudGestionArchivo],
        observacion_id: Optional[int] = None,
    ) -> list[int]:
        ...

    @abstractmethod
    def link_archivos_observacion(self, observacion_id: int, archivo_ids: list[int]) -> None:
        ...

    @abstractmethod
    def count_archivos_categoria(self, solicitud_id: int, categoria: str) -> int:
        ...

    @abstractmethod
    def add_observacion(
        self,
        solicitud_id: int,
        observacion: SolicitudGestionObservacion,
    ) -> SolicitudGestionObservacion:
        ...

    @abstractmethod
    def get_observaciones(self, solicitud_id: int) -> list[SolicitudGestionObservacion]:
        ...

    @abstractmethod
    def get_observacion_by_id(self, observacion_id: int) -> Optional[SolicitudGestionObservacion]:
        ...

    @abstractmethod
    def update_observacion_contenido(self, observacion_id: int, contenido: str) -> None:
        ...

    @abstractmethod
    def update_productos_estado_aprobacion(
        self,
        solicitud_id: int,
        estados_por_id: dict[int, str],
    ) -> None:
        ...

    @abstractmethod
    def get_historial(self, solicitud_id: int) -> list[SolicitudGestionHistorialEstado]:
        ...
