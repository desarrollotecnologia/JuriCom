"""Punto de entrada de la aplicación FastAPI.

Ejecutar:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.infrastructure.config import settings
from app.infrastructure.database.bootstrap import init_database, seed_admin_user
from app.presentation.api.v1.router import api_v1_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando base de datos...")
    try:
        init_database()
        seed_admin_user()
    except Exception as e:
        # No tumbamos el servidor por fallas de BD: registramos y seguimos.
        # Cuando se solucionen los permisos, basta con reiniciar la app.
        logger.error(
            "Fallo al inicializar BD: %s. El servidor arranca igualmente; "
            "los endpoints que toquen MySQL devolverán error 500 hasta que "
            "se solucione la conectividad/permisos.",
            e,
        )
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)
    logger.info("Aplicación lista en %s:%s", settings.APP_HOST, settings.APP_PORT)
    yield


app = FastAPI(
    title="JURICOM_BEEF",
    description=(
        "Sistema de gestión de contratos para los roles de Jurídica y Compras "
        "de Colbeef. Construido con Clean Architecture."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else [
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


FRONTEND_DIR = (Path(__file__).resolve().parents[1] / "frontend" / "public").resolve()
if FRONTEND_DIR.exists():
    app.mount(
        "/app",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )

    FRONTEND_SRC = (Path(__file__).resolve().parents[1] / "frontend" / "src").resolve()
    if FRONTEND_SRC.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(FRONTEND_SRC)),
            name="frontend-src",
        )


@app.get("/", include_in_schema=False)
def root():
    if FRONTEND_DIR.exists():
        return RedirectResponse(url="/app/login.html")
    return {"message": "Juridica · Colbeef API", "docs": "/docs"}


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
