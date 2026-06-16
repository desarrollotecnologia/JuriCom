"""Agregador de routers v1."""

from fastapi import APIRouter

from app.presentation.api.v1.endpoints import (
    archivos,
    auth,
    config,
    contratos,
    notifications,
    solicitudes_gestion,
    tareas,
    users,
)


api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(contratos.router)
api_v1_router.include_router(solicitudes_gestion.router)
api_v1_router.include_router(archivos.router)
api_v1_router.include_router(notifications.router)
api_v1_router.include_router(config.router)
api_v1_router.include_router(tareas.router)
