"""Interfaz del repositorio de contratos."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.contrato import ArchivoAdjunto, Contrato
from app.domain.entities.otrosi import Otrosi
from app.domain.value_objects.estado_aprobacion import EstadoAprobacion
from app.domain.value_objects.estado_contrato import EstadoContrato


class ContratoRepository(ABC):
    @abstractmethod
    def create(self, contrato: Contrato) -> Contrato: ...

    @abstractmethod
    def update(self, contrato: Contrato) -> Contrato: ...

    @abstractmethod
    def delete(self, contrato_id: int) -> bool: ...

    @abstractmethod
    def add_archivo(self, archivo: ArchivoAdjunto) -> ArchivoAdjunto: ...

    @abstractmethod
    def add_otrosi(self, otrosi: Otrosi) -> Otrosi: ...

    @abstractmethod
    def update_otrosi(self, otrosi: Otrosi) -> Otrosi: ...

    @abstractmethod
    def get_otrosi(self, otrosi_id: int) -> Optional[Otrosi]: ...

    @abstractmethod
    def list_otrosies_by_estado_aprobacion(
        self, estado: EstadoAprobacion
    ) -> list[tuple[Contrato, Otrosi]]: ...

    @abstractmethod
    def get_by_id(self, contrato_id: int) -> Optional[Contrato]: ...

    @abstractmethod
    def get_by_codigo(self, codigo: str) -> Optional[Contrato]: ...

    @abstractmethod
    def list_all(self) -> list[Contrato]: ...

    @abstractmethod
    def list_by_creador(self, user_id: int) -> list[Contrato]: ...

    @abstractmethod
    def user_has_related_records(self, user_id: int) -> bool: ...

    @abstractmethod
    def list_by_estado(self, estado: EstadoContrato) -> list[Contrato]: ...

    @abstractmethod
    def search(
        self,
        *,
        query: Optional[str] = None,
        estado: Optional[EstadoContrato] = None,
        creador_id: Optional[int] = None,
        solo_aprobados: bool = False,
    ) -> list[Contrato]: ...
