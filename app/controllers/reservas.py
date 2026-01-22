# app/controllers/reservas.py
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, date

from app.database import (
    fetch_all_reservas,
    fetch_all_clientes,
    fetch_all_vehiculos,
    insert_reserva,
    fetch_reserva_by_id,
    update_reserva,
    DatabaseConnectionError,
)
from app.schemas import ReservaBase

logger = logging.getLogger("autorent")
router = APIRouter()


def _to_iso(v: Any) -> Any:
    """Convert datetime/date to ISO string; leave other types unchanged."""
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _normalize_reserva_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a DB row (dict-like) into a JSON-safe dict for templates.
    - datetime/date -> ISO string
    - numeric-like total_estimado -> float or None
    - keep other fields as-is (but convert to primitive types where possible)
    """
    r = dict(row)  # shallow copy to avoid mutating original
    # Normalize date/time fields commonly present in reservas
    for fld in ("fecha_inicio", "fecha_fin", "fecha_reserva"):
        if fld in r:
            r[fld] = _to_iso(r[fld])

    # Normalize total_estimado to float or None
    te = r.get("total_estimado")
    if te is None:
        r["total_estimado"] = None
    else:
        try:
            r["total_estimado"] = float(te)
        except Exception:
            # If conversion fails (e.g., unexpected string), set to None
            r["total_estimado"] = None

    # Ensure nested values (cliente_nombre, cliente_apellido, vehiculo_matricula) are strings
    for k in ("cliente_nombre", "cliente_apellido", "vehiculo_matricula"):
        if k in r and r[k] is not None:
            r[k] = str(r[k])

    return r


def _normalize_list(rows: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    return [_normalize_reserva_row(r) for r in rows]


def _normalize_simple_list(rows: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Normalize lists of clientes/vehiculos: convert any date/datetime to ISO strings
    and ensure values are primitives for JSON serialization.
    """
    if not rows:
        return []
    out: List[Dict[str, Any]] = []
    for item in rows:
        d = dict(item)
        for k, v in list(d.items()):
            if isinstance(v, (datetime, date)):
                d[k] = v.isoformat()
            else:
                # convert Decimal or other types to str/float where appropriate
                try:
                    # try numeric conversion for numbers stored as strings
                    if isinstance(v, str):
                        # leave strings as-is
                        d[k] = v
                    else:
                        d[k] = v
                except Exception:
                    d[k] = str(v)
        out.append(d)
    return out


@router.get("/reservas", response_class=HTMLResponse)
def get_reservas(request: Request):
    """
    Render the reservas page. We pass JSON-safe lists to the template and ensure
    the variable used by templates with tojson is already serializable.
    """
    try:
        reservas_rows = fetch_all_reservas() or []
        clientes_rows = fetch_all_clientes() or []
        vehiculos_rows = fetch_all_vehiculos() or []

        # Create JSON-safe versions (dicts with ISO dates and primitive types)
        reservas_json = _normalize_list(reservas_rows)
        clientes_json = _normalize_simple_list(clientes_rows)
        vehiculos_json = _normalize_simple_list(vehiculos_rows)

        # IMPORTANT: pass the JSON-safe lists as "reservas", "clientes", "vehiculos"
        # so templates that call `r | tojson` operate on serializable dicts.
        return request.app.state.templates.TemplateResponse(
            "pages/reservas.html",
            {
                "request": request,
                "reservas": reservas_json,
                "clientes": clientes_json,
                "vehiculos": vehiculos_json,
                # keep explicit *_json names for templates that expect them
                "reservas_json": reservas_json,
                "clientes_json": clientes_json,
                "vehiculos_json": vehiculos_json,
            },
        )
    except DatabaseConnectionError:
        # Let the global handler render the friendly DB error page
        raise
    except Exception as exc:
        logger.exception("Error al obtener reservas: %s", exc)
        # Re-raise as HTTPException so global handler can catch and render error page
        raise HTTPException(status_code=500, detail="Error interno al obtener reservas")


@router.get("/reservas/nueva", response_class=HTMLResponse)
def get_nueva_reserva(request: Request):
    try:
        clientes_rows = fetch_all_clientes() or []
        vehiculos_rows = fetch_all_vehiculos() or []

        clientes_json = _normalize_simple_list(clientes_rows)
        vehiculos_json = _normalize_simple_list(vehiculos_rows)

        return request.app.state.templates.TemplateResponse(
            "pages/nueva_reserva.html",
            {
                "request": request,
                "clientes": clientes_json,
                "vehiculos": vehiculos_json,
                "clientes_json": clientes_json,
                "vehiculos_json": vehiculos_json,
            },
        )
    except DatabaseConnectionError:
        raise
    except Exception as exc:
        logger.exception("Error al preparar formulario nueva reserva: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno al preparar formulario")


@router.post("/reservas/nueva")
def post_nueva_reserva(
    request: Request,
    cliente_id: int = Form(...),
    vehiculo_id: int = Form(...),
    empleado_id: Optional[str] = Form(None),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    total_estimado: Optional[str] = Form(None),
    notas: Optional[str] = Form(None),
):
    try:
        empleado_id_int = None
        if empleado_id is not None and str(empleado_id).strip() != "":
            try:
                empleado_id_int = int(empleado_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="Empleado inválido")

        total_estimado_float = None
        if total_estimado is not None and str(total_estimado).strip() != "":
            try:
                total_estimado_float = float(total_estimado)
            except ValueError:
                raise HTTPException(status_code=422, detail="Total estimado inválido")

        reserva_data = ReservaBase(
            cliente_id=int(cliente_id),
            vehiculo_id=int(vehiculo_id),
            empleado_id=empleado_id_int,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_estimado=total_estimado_float,
            notas=notas if notas else None,
        )

        insert_reserva(
            reserva_data.cliente_id,
            reserva_data.vehiculo_id,
            reserva_data.empleado_id,
            reserva_data.fecha_inicio,
            reserva_data.fecha_fin,
            reserva_data.estado,
            reserva_data.total_estimado,
            reserva_data.notas,
        )

        return RedirectResponse(url="/reservas", status_code=303)
    except DatabaseConnectionError:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error al insertar reserva: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno al insertar reserva")


@router.get("/reservas/editar/{reserva_id}", response_class=HTMLResponse)
def get_editar_reserva(request: Request, reserva_id: int):
    try:
        reserva_row = fetch_reserva_by_id(reserva_id)
        if not reserva_row:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        reserva_json = _normalize_reserva_row(reserva_row)

        clientes_rows = fetch_all_clientes() or []
        vehiculos_rows = fetch_all_vehiculos() or []
        clientes_json = _normalize_simple_list(clientes_rows)
        vehiculos_json = _normalize_simple_list(vehiculos_rows)

        return request.app.state.templates.TemplateResponse(
            "pages/editar_reserva.html",
            {
                "request": request,
                "reserva": reserva_json,
                "reserva_json": reserva_json,
                "clientes": clientes_json,
                "vehiculos": vehiculos_json,
                "clientes_json": clientes_json,
                "vehiculos_json": vehiculos_json,
            },
        )
    except DatabaseConnectionError:
        raise
    except Exception as exc:
        logger.exception("Error al obtener reserva para editar: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno al obtener reserva")


@router.post("/reservas/editar/{reserva_id}")
def post_editar_reserva(
    request: Request,
    reserva_id: int,
    cliente_id: int = Form(...),
    vehiculo_id: int = Form(...),
    empleado_id: Optional[str] = Form(None),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    estado: str = Form(...),
    total_estimado: Optional[str] = Form(None),
    notas: Optional[str] = Form(None),
):
    try:
        empleado_id_int = None
        if empleado_id is not None and str(empleado_id).strip() != "":
            try:
                empleado_id_int = int(empleado_id)
            except ValueError:
                raise HTTPException(status_code=422, detail="Empleado inválido")

        total_estimado_float = None
        if total_estimado is not None and str(total_estimado).strip() != "":
            try:
                total_estimado_float = float(total_estimado)
            except ValueError:
                raise HTTPException(status_code=422, detail="Total estimado inválido")

        reserva_data = ReservaBase(
            cliente_id=int(cliente_id),
            vehiculo_id=int(vehiculo_id),
            empleado_id=empleado_id_int,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
            total_estimado=total_estimado_float,
            notas=notas if notas else None,
        )

        actualizado = update_reserva(
            reserva_id,
            reserva_data.cliente_id,
            reserva_data.vehiculo_id,
            reserva_data.empleado_id,
            reserva_data.fecha_inicio,
            reserva_data.fecha_fin,
            reserva_data.estado,
            reserva_data.total_estimado,
            reserva_data.notas,
        )

        if not actualizado:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        return RedirectResponse(url="/reservas", status_code=303)
    except DatabaseConnectionError:
        raise
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error al actualizar reserva")
        raise HTTPException(status_code=500, detail="Error interno al actualizar reserva")