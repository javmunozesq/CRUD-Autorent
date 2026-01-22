# app/controllers/clientes.py
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
import logging

from app.database import (
    fetch_all_clientes,
    insert_cliente,
    delete_cliente,
    fetch_cliente_by_id,
    update_cliente,
    DatabaseConnectionError,
)
from app.schemas import ClienteCreate, ClienteUpdate, ClienteDB

logger = logging.getLogger("autorent")
router = APIRouter()


def _is_ajax(request: Request) -> bool:
    """
    Detecta peticiones AJAX/fetch:
    - X-Requested-With: XMLHttpRequest (convencional)
    - Accept header contains 'application/json' (fetch expecting JSON)
    """
    xrw = (request.headers.get("x-requested-with") or "").lower()
    accept = (request.headers.get("accept") or "").lower()
    if xrw == "xmlhttprequest":
        return True
    if "application/json" in accept:
        return True
    return False


@router.get("/clientes", response_class=HTMLResponse)
def get_clientes(request: Request):
    try:
        clientes_rows = fetch_all_clientes() or []
        clientes = [ClienteDB(**r) for r in clientes_rows] if clientes_rows else []
        return request.app.state.templates.TemplateResponse(
            "pages/index.html", {"request": request, "clientes": clientes}
        )
    except DatabaseConnectionError:
        # Dejar que el manejador global muestre pages/error404.html
        raise
    except Exception:
        logger.exception("Error al cargar la página de clientes")
        raise HTTPException(status_code=500, detail="Error interno al cargar clientes")


@router.get("/clientes/nuevo", response_class=HTMLResponse)
def get_nuevo_cliente(request: Request):
    return request.app.state.templates.TemplateResponse(
        "pages/nuevo_cliente.html", {"request": request, "mensaje": None}
    )


@router.get("/clientes/crear", response_class=HTMLResponse)
def get_crear_cliente(request: Request):
    return request.app.state.templates.TemplateResponse(
        "pages/nuevo_cliente.html", {"request": request, "mensaje": None}
    )


@router.post("/clientes/nuevo")
def post_nuevo_cliente(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(...),
    email: str = Form(...),
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
):
    try:
        cliente_data = ClienteCreate(
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono if telefono else None,
            direccion=direccion if direccion else None,
        )
        insert_cliente(
            cliente_data.nombre,
            cliente_data.apellido,
            cliente_data.email,
            cliente_data.telefono,
            cliente_data.direccion,
        )
        return RedirectResponse(url="/", status_code=303)
    except DatabaseConnectionError:
        # Dejar que el manejador global muestre pages/error404.html
        raise
    except Exception:
        logger.exception("Error al insertar cliente")
        return request.app.state.templates.TemplateResponse(
            "pages/nuevo_cliente.html",
            {
                "request": request,
                "mensaje": None,
                "errores": ["Error interno al insertar cliente"],
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
            },
            status_code=500,
        )


@router.delete("/clientes/{cliente_id}")
def delete_cliente_endpoint(request: Request, cliente_id: int):
    """
    Elimina un cliente. Si la eliminación falla por cualquier motivo (no existe,
    error de BD, etc.) redirige a /error404 para peticiones normales o devuelve
    JSON con {"redirect": "/error404"} para peticiones AJAX (fetch/XHR).
    """
    try:
        eliminado = delete_cliente(cliente_id)
        if not eliminado:
            # Cliente no encontrado o no se pudo eliminar
            if _is_ajax(request):
                return JSONResponse(content={"redirect": "/error404"}, status_code=200)
            return RedirectResponse(url="/error404", status_code=303)

        # Eliminado correctamente
        return JSONResponse(content={"mensaje": "Cliente eliminado exitosamente"}, status_code=200)

    except DatabaseConnectionError:
        # Base de datos caída: redirigir al usuario a la página de error
        logger.exception("DatabaseConnectionError al eliminar cliente")
        if _is_ajax(request):
            return JSONResponse(content={"redirect": "/error404"}, status_code=200)
        return RedirectResponse(url="/error404", status_code=303)
    except Exception:
        logger.exception("Error inesperado al eliminar cliente")
        if _is_ajax(request):
            return JSONResponse(content={"redirect": "/error404"}, status_code=200)
        return RedirectResponse(url="/error404", status_code=303)


@router.get("/clientes/editar/{cliente_id}", response_class=HTMLResponse)
def get_editar_cliente(request: Request, cliente_id: int):
    try:
        cliente_data = fetch_cliente_by_id(cliente_id)
        if not cliente_data:
            # Redirigir a la página de error si no existe
            return RedirectResponse(url="/error404", status_code=303)
        cliente = ClienteDB(**cliente_data)
        return request.app.state.templates.TemplateResponse(
            "pages/editar_cliente.html", {"request": request, "cliente": cliente}
        )
    except DatabaseConnectionError:
        raise
    except Exception:
        logger.exception("Error al obtener cliente para editar")
        raise HTTPException(status_code=500, detail="Error interno al obtener cliente")


@router.post("/clientes/editar/{cliente_id}")
def post_editar_cliente(
    request: Request,
    cliente_id: int,
    nombre: str = Form(...),
    apellido: str = Form(...),
    email: str = Form(...),
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
):
    try:
        cliente_data = ClienteUpdate(
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono if telefono else None,
            direccion=direccion if direccion else None,
        )
        actualizado = update_cliente(
            cliente_id,
            cliente_data.nombre,
            cliente_data.apellido,
            cliente_data.email,
            cliente_data.telefono,
            cliente_data.direccion,
        )
        if not actualizado:
            return RedirectResponse(url="/error404", status_code=303)
        return RedirectResponse(url="/", status_code=303)
    except DatabaseConnectionError:
        raise
    except Exception:
        logger.exception("Error al actualizar cliente")
        raise HTTPException(status_code=500, detail="Error interno al actualizar cliente")