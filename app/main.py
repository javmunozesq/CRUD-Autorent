# app/main.py
import importlib
import logging
from typing import Any, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader

# Import database helpers and exception (seguro: no importan controllers aquí)
from app.database import (
    fetch_all_clientes,
    fetch_all_vehiculos,
    fetch_all_reservas,
    DatabaseConnectionError,
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autorent")

# --- Create the FastAPI app immediately so module always exposes `app` ---
app = FastAPI(title="Autorent")

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates: allow includes from pages/, pages and components/
templates = Jinja2Templates(directory="app/templates")
templates.env.loader = ChoiceLoader(
    [
        FileSystemLoader("app/templates"),
        FileSystemLoader("app/templates/pages"),
        FileSystemLoader("app/templates/components"),
    ]
)

# Save templates in app state so controllers can access them via request.app.state.templates
app.state.templates = templates

# Favicon route
@app.get("/favicon.ico")
def favicon():
    return RedirectResponse(url="/static/img/favicon.ico")


# ----------------------------
# Helpers to convert models/rows to JSON-serializable dicts for templates
# ----------------------------
def model_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return obj


def list_models_to_dicts(items: List[Any]) -> List[Any]:
    return [model_to_dict(i) for i in items]


# ----------------------------
# Global exception handlers
# ----------------------------
@app.exception_handler(DatabaseConnectionError)
async def db_connection_exception_handler(request: Request, exc: DatabaseConnectionError):
    logger.exception("DatabaseConnectionError capturada: %s", exc)
    try:
        return templates.TemplateResponse(
            "pages/error404.html", {"request": request, "error": str(exc)}, status_code=404
        )
    except Exception:
        return JSONResponse(
            content={"detail": "No se pudo conectar a la base de datos."}, status_code=404
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception capturada: %s", exc)
    try:
        return templates.TemplateResponse(
            "pages/error404.html", {"request": request, "error": str(exc)}, status_code=500
        )
    except Exception:
        return JSONResponse(content={"detail": "Error interno del servidor."}, status_code=500)


# ----------------------------
# Dynamically import and include controllers (avoids circular imports)
# ----------------------------
def _include_controllers():
    """
    Import controllers dynamically and include their routers.
    Each controller module should expose a router variable named <resource>_router
    (e.g., clientes_router, vehiculos_router, reservas_router, pagos_router).
    This function tolera la ausencia de módulos para no romper el arranque.
    """
    controller_modules = [
        "app.controllers.clientes",
        "app.controllers.vehiculos",
        "app.controllers.reservas",
        "app.controllers.pagos",
    ]
    for mod_name in controller_modules:
        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            logger.debug("Controller module not found: %s", mod_name)
            continue
        except Exception:
            logger.exception("Error importing controller module %s", mod_name)
            continue

        # Include any attribute that ends with "_router"
        for attr in dir(mod):
            if attr.endswith("_router"):
                router = getattr(mod, attr)
                try:
                    app.include_router(router)
                    logger.info("Included router %s from %s", attr, mod_name)
                except Exception:
                    logger.exception("Failed to include router %s from %s", attr, mod_name)


# Call the include function after app and templates are ready
_include_controllers()


# ----------------------------
# Root route: render index page (intenta cargar datos; si falla, el handler global mostrará error404)
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    try:
        clientes_rows = fetch_all_clientes() or []
        vehiculos_rows = fetch_all_vehiculos() or []
        reservas_rows = fetch_all_reservas() or []

        clientes_json = list_models_to_dicts(clientes_rows)
        vehiculos_json = list_models_to_dicts(vehiculos_rows)
        reservas_json = list_models_to_dicts(reservas_rows)

        return templates.TemplateResponse(
            "pages/index.html",
            {
                "request": request,
                "clientes": clientes_rows,
                "vehiculos": vehiculos_rows,
                "reservas": reservas_rows,
                "clientes_json": clientes_json,
                "vehiculos_json": vehiculos_json,
                "reservas_json": reservas_json,
            },
        )
    except DatabaseConnectionError:
        raise
    except Exception:
        logger.exception("Error al renderizar la página principal")
        raise


# Health check
@app.get("/health")
def health_check():
    return JSONResponse(content={"status": "ok", "service": "autorent"}, status_code=200)


# Endpoint para mostrar la página de error manualmente si se desea
@app.get("/error404", response_class=HTMLResponse)
def get_error404(request: Request):
    try:
        return templates.TemplateResponse(
            "pages/error404.html",
            {
                "request": request,
                "mensaje": "Ha ocurrido un error. Comprueba la conexión a la base de datos o contacta con el administrador.",
            },
            status_code=404,
        )
    except Exception:
        return JSONResponse(
            content={"detail": "Error crítico: no se pudo renderizar la página de error."}, status_code=500
        )