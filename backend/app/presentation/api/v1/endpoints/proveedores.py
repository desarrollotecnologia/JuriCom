"""Catálogo de proveedores.

- Lo llenan/editan Compras y Admin (importando el Excel o a mano).
- Cualquier usuario autenticado puede pedir *sugerencias* al crear una
  solicitud de servicios (según título + descripción + centro de costo).
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.infrastructure.catalogos.proveedores_excel import (
    normalizar_texto,
    parse_catalogo_proveedores,
)
from app.infrastructure.catalogos.proveedores_match import rankear_proveedores
from app.infrastructure.config import settings
from app.infrastructure.database.models import ProveedorModel
from app.infrastructure.database.session import get_db
from app.presentation.api.v1.dependencies import (
    get_current_user,
    require_compras_o_admin,
)


router = APIRouter(prefix="/proveedores", tags=["proveedores"])

_PARA_VALIDAS = {"servicios", "compras", "ambas", ""}


class ProveedorIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=300)
    sector: str = Field("", max_length=500)
    para: str = Field("", max_length=20)
    ciudad: str = Field("", max_length=200)
    telefono: str = Field("", max_length=200)
    correo: str = Field("", max_length=300)
    contacto: str = Field("", max_length=300)
    condiciones_pago: str = Field("", max_length=200)
    calificacion: str = Field("", max_length=100)
    activo: bool = True


class ProveedorOut(ProveedorIn):
    id: int
    score: Optional[int] = None


def _to_out(m: ProveedorModel, score: Optional[int] = None) -> ProveedorOut:
    return ProveedorOut(
        id=m.id,
        nombre=m.nombre,
        sector=m.sector,
        para=m.para,
        ciudad=m.ciudad,
        telefono=m.telefono,
        correo=m.correo,
        contacto=m.contacto,
        condiciones_pago=m.condiciones_pago,
        calificacion=m.calificacion,
        activo=m.activo,
        score=score,
    )


def _normalizar_para(valor: str) -> str:
    v = (valor or "").strip().lower()
    return v if v in _PARA_VALIDAS else ""


@router.get("/sugerencias", response_model=list[ProveedorOut])
def sugerencias(
    q: str,
    solo_servicios: bool = True,
    top: int = 8,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProveedorOut]:
    """Mejores proveedores para un servicio, según las palabras de `q`."""
    filas = db.query(ProveedorModel).filter(ProveedorModel.activo.is_(True)).all()
    datos = [
        {
            "id": m.id,
            "nombre": m.nombre,
            "sector": m.sector,
            "para": m.para,
            "ciudad": m.ciudad,
            "telefono": m.telefono,
            "correo": m.correo,
            "contacto": m.contacto,
            "condiciones_pago": m.condiciones_pago,
            "calificacion": m.calificacion,
            "activo": m.activo,
        }
        for m in filas
    ]
    rank = rankear_proveedores(
        q, datos, solo_servicios=solo_servicios, top=max(1, min(top, 30))
    )
    return [
        ProveedorOut(**{k: v for k, v in p.items() if k != "_score"}, score=p["_score"])
        for p in rank
    ]


@router.get("/opciones", response_model=list[ProveedorOut])
def opciones(
    solo_servicios: bool = False,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProveedorOut]:
    """Lista para el buscador del formulario (cualquier usuario autenticado).

    Todos los proveedores activos. Se puede acotar a servicios con
    `?solo_servicios=true`."""
    query = db.query(ProveedorModel).filter(ProveedorModel.activo.is_(True))
    if solo_servicios:
        query = query.filter(ProveedorModel.para.in_(("servicios", "ambas")))
    filas = query.order_by(ProveedorModel.nombre.asc()).all()
    return [_to_out(m) for m in filas]


@router.get("", response_model=list[ProveedorOut])
def listar(
    q: str = "",
    _: User = Depends(require_compras_o_admin),
    db: Session = Depends(get_db),
) -> list[ProveedorOut]:
    query = db.query(ProveedorModel)
    termino = q.strip()
    if termino:
        like = f"%{termino}%"
        query = query.filter(
            or_(
                ProveedorModel.nombre.ilike(like),
                ProveedorModel.sector.ilike(like),
                ProveedorModel.ciudad.ilike(like),
            )
        )
    filas = query.order_by(ProveedorModel.nombre.asc()).all()
    return [_to_out(m) for m in filas]


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear(
    payload: ProveedorIn,
    _: User = Depends(require_compras_o_admin),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    nombre = payload.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio.")
    m = ProveedorModel(
        nombre=nombre,
        sector=payload.sector.strip(),
        para=_normalizar_para(payload.para),
        ciudad=payload.ciudad.strip(),
        telefono=payload.telefono.strip(),
        correo=payload.correo.strip(),
        contacto=payload.contacto.strip(),
        condiciones_pago=payload.condiciones_pago.strip(),
        calificacion=payload.calificacion.strip(),
        activo=payload.activo,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _to_out(m)


@router.put("/{proveedor_id}", response_model=ProveedorOut)
def actualizar(
    proveedor_id: int,
    payload: ProveedorIn,
    _: User = Depends(require_compras_o_admin),
    db: Session = Depends(get_db),
) -> ProveedorOut:
    m = db.get(ProveedorModel, proveedor_id)
    if m is None:
        raise HTTPException(status_code=404, detail="No existe el proveedor.")
    if not payload.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio.")
    m.nombre = payload.nombre.strip()
    m.sector = payload.sector.strip()
    m.para = _normalizar_para(payload.para)
    m.ciudad = payload.ciudad.strip()
    m.telefono = payload.telefono.strip()
    m.correo = payload.correo.strip()
    m.contacto = payload.contacto.strip()
    m.condiciones_pago = payload.condiciones_pago.strip()
    m.calificacion = payload.calificacion.strip()
    m.activo = payload.activo
    db.commit()
    db.refresh(m)
    return _to_out(m)


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    proveedor_id: int,
    _: User = Depends(require_compras_o_admin),
    db: Session = Depends(get_db),
) -> None:
    m = db.get(ProveedorModel, proveedor_id)
    if m is None:
        raise HTTPException(status_code=404, detail="No existe el proveedor.")
    db.delete(m)
    db.commit()


@router.post("/importar")
def importar_excel(
    archivo: UploadFile = File(..., description="Excel del catálogo de proveedores."),
    _: User = Depends(require_compras_o_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Carga masiva desde Excel. Upsert por nombre (no duplica)."""
    contenido = archivo.file.read()
    if len(contenido) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    try:
        provs = parse_catalogo_proveedores(contenido)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"No se pudo leer el Excel: {e}")

    existentes = {normalizar_texto(m.nombre): m for m in db.query(ProveedorModel).all()}
    creados = 0
    actualizados = 0
    for p in provs:
        clave = normalizar_texto(p["nombre"])
        m = existentes.get(clave)
        if m is None:
            m = ProveedorModel(**p)
            db.add(m)
            existentes[clave] = m
            creados += 1
        else:
            # Solo rellena datos faltantes; no pisa lo que Compras ya editó.
            for campo in ("sector", "ciudad", "telefono", "correo", "contacto",
                          "condiciones_pago", "calificacion"):
                if not getattr(m, campo) and p.get(campo):
                    setattr(m, campo, p[campo])
            if not m.para and p.get("para"):
                m.para = p["para"]
            actualizados += 1
    db.commit()
    return {"creados": creados, "actualizados": actualizados, "total": len(provs)}
