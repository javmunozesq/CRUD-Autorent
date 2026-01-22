# app/controllers/pagos.py
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from app.database import insert_pago, fetch_pagos_by_reserva

logger = logging.getLogger("autorent")
router = APIRouter()

@router.post("/pagos/nuevo")
def post_nuevo_pago(
    reserva_id: int = Form(...),
    monto: float = Form(...),
    metodo_pago: str = Form(...),
    referencia: Optional[str] = Form(None)
):
    if monto <= 0:
        raise HTTPException(status_code=422, detail="Monto debe ser mayor que 0")

    pago_id = insert_pago(reserva_id, monto, metodo_pago, referencia)
    if not pago_id:
        raise HTTPException(status_code=400, detail="No se pudo registrar el pago")

    return JSONResponse(content={"mensaje": "Pago registrado", "pago_id": pago_id}, status_code=201)

@router.get("/pagos/{reserva_id}", response_class=JSONResponse)
def get_pagos_reserva(reserva_id: int):
    pagos = fetch_pagos_by_reserva(reserva_id)
    return JSONResponse(content={"pagos": pagos}, status_code=200)