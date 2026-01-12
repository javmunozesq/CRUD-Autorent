# app/main.py
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, field_validator, ValidationError
from typing import Optional, List
import re

# Importamos las funciones que consultan/insertan/eliminan en MariaDB (archivo app/database.py)
from app.database import (
    # Clientes
    fetch_all_clientes,
    insert_cliente,
    delete_cliente,
    fetch_cliente_by_id,
    update_cliente,
    # Vehículos
    fetch_all_vehiculos,
    insert_vehiculo,
    delete_vehiculo,
    fetch_vehiculo_by_id,
    update_vehiculo,
    # Modelos y categorías
    fetch_all_modelos,
    fetch_all_categorias,
    # Reservas y pagos
    fetch_all_reservas,
    insert_reserva,
    delete_reserva,
    fetch_reserva_by_id,
    update_reserva,
    insert_pago,
    fetch_pagos_by_reserva
)

# ----------------------------
# Modelos Pydantic y validaciones
# ----------------------------

# Reutilizamos validaciones para nombres
def validar_texto_nombre(v: str, campo: str = "campo") -> str:
    if not v or not v.strip():
        raise ValueError(f'{campo} no puede estar vacío')
    v = v.strip()
    if len(v) < 2:
        raise ValueError(f'{campo} debe tener al menos 2 caracteres')
    if len(v) > 50:
        raise ValueError(f'{campo} no puede exceder 50 caracteres')
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', v):
        raise ValueError(f'{campo} solo permite letras y espacios')
    return v.title()


class ClienteBase(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None

    @field_validator('nombre', 'apellido')
    @classmethod
    def validar_nombre_apellido(cls, v: str) -> str:
        return validar_texto_nombre(v, "Nombre/Apellido")

    @field_validator('telefono')
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == '':
            return None
        v = v.strip()
        telefono_limpio = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?\d{7,15}$', telefono_limpio):
            raise ValueError('Formato de teléfono inválido. Debe contener entre 7 y 15 dígitos')
        return v

    @field_validator('direccion')
    @classmethod
    def validar_direccion(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == '':
            return None
        v = v.strip()
        if len(v) > 200:
            raise ValueError('La dirección no puede exceder 200 caracteres')
        return v


class ClienteDB(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str
    telefono: Optional[str] = None
    direccion: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(ClienteBase):
    pass


class VehiculoBase(BaseModel):
    matricula: str
    vin: Optional[str] = None
    modelo_id: int
    color: Optional[str] = None
    kilometraje: Optional[int] = 0
    estado: Optional[str] = "disponible"
    precio_dia: float
    ubicacion: Optional[str] = None

    @field_validator('matricula')
    @classmethod
    def validar_matricula(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Matrícula no puede estar vacía')
        v = v.strip().upper()
        if len(v) > 20:
            raise ValueError('Matrícula demasiado larga')
        return v

    @field_validator('precio_dia')
    @classmethod
    def validar_precio(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError('El precio por día debe ser mayor que 0')
        return round(v, 2)


class VehiculoDB(VehiculoBase):
    id: int


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(VehiculoBase):
    pass


class ReservaBase(BaseModel):
    cliente_id: int
    vehiculo_id: int
    empleado_id: Optional[int] = None
    fecha_inicio: str  # ISO datetime string esperado desde formulario
    fecha_fin: str
    estado: Optional[str] = "pendiente"
    total_estimado: Optional[float] = None
    notas: Optional[str] = None

    @field_validator('fecha_inicio', 'fecha_fin')
    @classmethod
    def validar_fecha_iso(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Fecha inválida')
        return v.strip()

    @field_validator('total_estimado')
    @classmethod
    def validar_total(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v < 0:
            raise ValueError('Total estimado no puede ser negativo')
        return round(v, 2)


class ReservaDB(ReservaBase):
    id: int
    fecha_reserva: Optional[str] = None


# ----------------------------
# App y configuración
# ----------------------------
app = FastAPI(title="Autorent")

# Servir archivos estáticos (asegúrate de que la carpeta exista)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Plantillas Jinja2 (asegúrate de que la carpeta exista)
templates = Jinja2Templates(directory="app/templates")


# ----------------------------
# Helpers para mapear filas a modelos
# ----------------------------
def map_rows_to_clientes(rows: List[dict]) -> List[ClienteDB]:
    return [
        ClienteDB(
            id=row["id"],
            nombre=row["nombre"],
            apellido=row["apellido"],
            email=row["email"],
            telefono=row.get("telefono"),
            direccion=row.get("direccion"),
        )
        for row in rows
    ]


def map_rows_to_vehiculos(rows: List[dict]) -> List[VehiculoDB]:
    return [
        VehiculoDB(
            id=row["id"],
            matricula=row["matricula"],
            vin=row.get("vin"),
            modelo_id=row["modelo_id"],
            color=row.get("color"),
            kilometraje=row.get("kilometraje", 0),
            estado=row.get("estado"),
            precio_dia=float(row["precio_dia"]),
            ubicacion=row.get("ubicacion")
        )
        for row in rows
    ]


def map_rows_to_reservas(rows: List[dict]) -> List[ReservaDB]:
    return [
        ReservaDB(
            id=row["id"],
            cliente_id=row["cliente_id"],
            vehiculo_id=row["vehiculo_id"],
            empleado_id=row.get("empleado_id"),
            fecha_inicio=str(row["fecha_inicio"]),
            fecha_fin=str(row["fecha_fin"]),
            estado=row.get("estado"),
            total_estimado=float(row["total_estimado"]) if row.get("total_estimado") is not None else None,
            notas=row.get("notas"),
            fecha_reserva=str(row.get("fecha_reserva")) if row.get("fecha_reserva") else None
        )
        for row in rows
    ]


# ----------------------------
# Rutas Clientes
# ----------------------------

@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    """
    Página principal: lista clientes, vehículos y reservas recientes.
    """
    clientes_rows = fetch_all_clientes()
    vehiculos_rows = fetch_all_vehiculos()
    reservas_rows = fetch_all_reservas()

    clientes = map_rows_to_clientes(clientes_rows)
    vehiculos = map_rows_to_vehiculos(vehiculos_rows)
    reservas = map_rows_to_reservas(reservas_rows)

    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "clientes": clientes,
            "vehiculos": vehiculos,
            "reservas": reservas
        }
    )


# --- Clientes: nuevo (formulario) ---
@app.get("/clientes/nuevo", response_class=HTMLResponse)
def get_nuevo_cliente(request: Request):
    return templates.TemplateResponse(
        "pages/nuevo_cliente.html",
        {"request": request, "mensaje": None}
    )


@app.post("/clientes/nuevo")
def post_nuevo_cliente(
    request: Request,
    nombre: str = Form(...),
    apellido: str = Form(...),
    email: str = Form(...),
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None)
):
    try:
        cliente_data = ClienteCreate(
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono if telefono else None,
            direccion=direccion if direccion else None
        )

        insert_cliente(
            cliente_data.nombre,
            cliente_data.apellido,
            cliente_data.email,
            cliente_data.telefono,
            cliente_data.direccion
        )

        return RedirectResponse(url="/", status_code=303)

    except ValidationError as e:
        errores = []
        for error in e.errors():
            campo = str(error['loc'][0]) if error['loc'] else 'campo'
            mensaje = error['msg']
            errores.append(f"{campo.capitalize()}: {mensaje}")

        return templates.TemplateResponse(
            "pages/nuevo_cliente.html",
            {
                "request": request,
                "mensaje": None,
                "errores": errores,
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion
            },
            status_code=422
        )


@app.delete("/clientes/{cliente_id}")
def delete_cliente_endpoint(cliente_id: int):
    eliminado = delete_cliente(cliente_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return JSONResponse(content={"mensaje": "Cliente eliminado exitosamente"}, status_code=200)


@app.get("/clientes/editar/{cliente_id}", response_class=HTMLResponse)
def get_editar_cliente(request: Request, cliente_id: int):
    cliente_data = fetch_cliente_by_id(cliente_id)
    if not cliente_data:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente = ClienteDB(**cliente_data)
    return templates.TemplateResponse(
        "pages/editar_cliente.html",
        {"request": request, "cliente": cliente}
    )


@app.post("/clientes/editar/{cliente_id}")
def post_editar_cliente(
    request: Request,
    cliente_id: int,
    nombre: str = Form(...),
    apellido: str = Form(...),
    email: str = Form(...),
    telefono: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None)
):
    try:
        cliente_data = ClienteUpdate(
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono if telefono else None,
            direccion=direccion if direccion else None
        )

        actualizado = update_cliente(
            cliente_id,
            cliente_data.nombre,
            cliente_data.apellido,
            cliente_data.email,
            cliente_data.telefono,
            cliente_data.direccion
        )

        if not actualizado:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        return RedirectResponse(url="/", status_code=303)

    except ValidationError as e:
        errores = []
        for error in e.errors():
            campo = str(error['loc'][0]) if error['loc'] else 'campo'
            mensaje = error['msg']
            errores.append(f"{campo.capitalize()}: {mensaje}")

        cliente_temp = ClienteDB(
            id=cliente_id,
            nombre=nombre,
            apellido=apellido,
            email=email,
            telefono=telefono,
            direccion=direccion
        )

        return templates.TemplateResponse(
            "pages/editar_cliente.html",
            {"request": request, "cliente": cliente_temp, "errores": errores},
            status_code=422
        )


# ----------------------------
# Rutas Vehículos
# ----------------------------

@app.get("/vehiculos", response_class=HTMLResponse)
def get_vehiculos(request: Request):
    vehiculos_rows = fetch_all_vehiculos()
    vehiculos = map_rows_to_vehiculos(vehiculos_rows)
    modelos = fetch_all_modelos()
    categorias = fetch_all_categorias()
    return templates.TemplateResponse(
        "pages/vehiculos.html",
        {
            "request": request,
            "vehiculos": vehiculos,
            "modelos": modelos,
            "categorias": categorias
        }
    )


@app.get("/vehiculos/nuevo", response_class=HTMLResponse)
def get_nuevo_vehiculo(request: Request):
    modelos = fetch_all_modelos()
    categorias = fetch_all_categorias()
    return templates.TemplateResponse(
        "pages/nuevo_vehiculo.html",
        {"request": request, "modelos": modelos, "categorias": categorias}
    )


@app.post("/vehiculos/nuevo")
def post_nuevo_vehiculo(
    request: Request,
    matricula: str = Form(...),
    vin: Optional[str] = Form(None),
    modelo_id: int = Form(...),
    color: Optional[str] = Form(None),
    kilometraje: Optional[int] = Form(0),
    estado: Optional[str] = Form("disponible"),
    precio_dia: float = Form(...),
    ubicacion: Optional[str] = Form(None)
):
    try:
        vehiculo_data = VehiculoCreate(
            matricula=matricula,
            vin=vin if vin else None,
            modelo_id=modelo_id,
            color=color if color else None,
            kilometraje=kilometraje if kilometraje else 0,
            estado=estado,
            precio_dia=precio_dia,
            ubicacion=ubicacion if ubicacion else None
        )

        insert_vehiculo(
            vehiculo_data.matricula,
            vehiculo_data.vin,
            vehiculo_data.modelo_id,
            vehiculo_data.color,
            vehiculo_data.kilometraje,
            vehiculo_data.estado,
            vehiculo_data.precio_dia,
            vehiculo_data.ubicacion
        )

        return RedirectResponse(url="/vehiculos", status_code=303)

    except ValidationError as e:
        errores = []
        for error in e.errors():
            campo = str(error['loc'][0]) if error['loc'] else 'campo'
            mensaje = error['msg']
            errores.append(f"{campo.capitalize()}: {mensaje}")

        modelos = fetch_all_modelos()
        categorias = fetch_all_categorias()

        return templates.TemplateResponse(
            "pages/nuevo_vehiculo.html",
            {
                "request": request,
                "errores": errores,
                "matricula": matricula,
                "vin": vin,
                "modelos": modelos,
                "categorias": categorias,
                "color": color,
                "kilometraje": kilometraje,
                "estado": estado,
                "precio_dia": precio_dia,
                "ubicacion": ubicacion
            },
            status_code=422
        )


@app.delete("/vehiculos/{vehiculo_id}")
def delete_vehiculo_endpoint(vehiculo_id: int):
    eliminado = delete_vehiculo(vehiculo_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return JSONResponse(content={"mensaje": "Vehículo eliminado exitosamente"}, status_code=200)


@app.get("/vehiculos/editar/{vehiculo_id}", response_class=HTMLResponse)
def get_editar_vehiculo(request: Request, vehiculo_id: int):
    vehiculo_data = fetch_vehiculo_by_id(vehiculo_id)
    if not vehiculo_data:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    vehiculo = VehiculoDB(**vehiculo_data)
    modelos = fetch_all_modelos()
    categorias = fetch_all_categorias()
    return templates.TemplateResponse(
        "pages/editar_vehiculo.html",
        {"request": request, "vehiculo": vehiculo, "modelos": modelos, "categorias": categorias}
    )


@app.post("/vehiculos/editar/{vehiculo_id}")
def post_editar_vehiculo(
    request: Request,
    vehiculo_id: int,
    matricula: str = Form(...),
    vin: Optional[str] = Form(None),
    modelo_id: int = Form(...),
    color: Optional[str] = Form(None),
    kilometraje: Optional[int] = Form(0),
    estado: Optional[str] = Form("disponible"),
    precio_dia: float = Form(...),
    ubicacion: Optional[str] = Form(None)
):
    try:
        vehiculo_data = VehiculoUpdate(
            matricula=matricula,
            vin=vin if vin else None,
            modelo_id=modelo_id,
            color=color if color else None,
            kilometraje=kilometraje if kilometraje else 0,
            estado=estado,
            precio_dia=precio_dia,
            ubicacion=ubicacion if ubicacion else None
        )

        actualizado = update_vehiculo(
            vehiculo_id,
            vehiculo_data.matricula,
            vehiculo_data.vin,
            vehiculo_data.modelo_id,
            vehiculo_data.color,
            vehiculo_data.kilometraje,
            vehiculo_data.estado,
            vehiculo_data.precio_dia,
            vehiculo_data.ubicacion
        )

        if not actualizado:
            raise HTTPException(status_code=404, detail="Vehículo no encontrado")

        return RedirectResponse(url="/vehiculos", status_code=303)

    except ValidationError as e:
        errores = []
        for error in e.errors():
            campo = str(error['loc'][0]) if error['loc'] else 'campo'
            mensaje = error['msg']
            errores.append(f"{campo.capitalize()}: {mensaje}")

        vehiculo_temp = VehiculoDB(
            id=vehiculo_id,
            matricula=matricula,
            vin=vin,
            modelo_id=modelo_id,
            color=color,
            kilometraje=kilometraje,
            estado=estado,
            precio_dia=precio_dia,
            ubicacion=ubicacion
        )

        modelos = fetch_all_modelos()
        categorias = fetch_all_categorias()

        return templates.TemplateResponse(
            "pages/editar_vehiculo.html",
            {"request": request, "vehiculo": vehiculo_temp, "errores": errores, "modelos": modelos, "categorias": categorias},
            status_code=422
        )


# ----------------------------
# Rutas Reservas y Pagos
# ----------------------------

@app.get("/reservas", response_class=HTMLResponse)
def get_reservas(request: Request):
    reservas_rows = fetch_all_reservas()
    reservas = map_rows_to_reservas(reservas_rows)
    clientes_rows = fetch_all_clientes()
    vehiculos_rows = fetch_all_vehiculos()
    clientes = map_rows_to_clientes(clientes_rows)
    vehiculos = map_rows_to_vehiculos(vehiculos_rows)
    return templates.TemplateResponse(
        "pages/reservas.html",
        {
            "request": request,
            "reservas": reservas,
            "clientes": clientes,
            "vehiculos": vehiculos
        }
    )


@app.get("/reservas/nueva", response_class=HTMLResponse)
def get_nueva_reserva(request: Request):
    clientes_rows = fetch_all_clientes()
    vehiculos_rows = fetch_all_vehiculos()
    clientes = map_rows_to_clientes(clientes_rows)
    vehiculos = map_rows_to_vehiculos(vehiculos_rows)
    return templates.TemplateResponse(
        "pages/nueva_reserva.html",
        {"request": request, "clientes": clientes, "vehiculos": vehiculos}
    )


@app.post("/reservas/nueva")
def post_nueva_reserva(
    request: Request,
    cliente_id: int = Form(...),
    vehiculo_id: int = Form(...),
    empleado_id: Optional[int] = Form(None),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    total_estimado: Optional[float] = Form(None),
    notas: Optional[str] = Form(None)
):
    try:
        reserva_data = ReservaBase(
            cliente_id=cliente_id,
            vehiculo_id=vehiculo_id,
            empleado_id=empleado_id if empleado_id else None,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_estimado=total_estimado if total_estimado is not None else None,
            notas=notas if notas else None
        )

        reserva_id = insert_reserva(
            reserva_data.cliente_id,
            reserva_data.vehiculo_id,
            reserva_data.empleado_id,
            reserva_data.fecha_inicio,
            reserva_data.fecha_fin,
            reserva_data.estado,
            reserva_data.total_estimado,
            reserva_data.notas
        )

        # Si se envía un pago inmediato, no lo gestionamos aquí por simplicidad.
        return RedirectResponse(url="/reservas", status_code=303)

    except ValidationError as e:
        errores = []
        for error in e.errors():
            campo = str(error['loc'][0]) if error['loc'] else 'campo'
            mensaje = error['msg']
            errores.append(f"{campo.capitalize()}: {mensaje}")

        clientes_rows = fetch_all_clientes()
        vehiculos_rows = fetch_all_vehiculos()
        clientes = map_rows_to_clientes(clientes_rows)
        vehiculos = map_rows_to_vehiculos(vehiculos_rows)

        return templates.TemplateResponse(
            "pages/nueva_reserva.html",
            {
                "request": request,
                "errores": errores,
                "clientes": clientes,
                "vehiculos": vehiculos,
                "cliente_id": cliente_id,
                "vehiculo_id": vehiculo_id,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "total_estimado": total_estimado,
                "notas": notas
            },
            status_code=422
        )


@app.delete("/reservas/{reserva_id}")
def delete_reserva_endpoint(reserva_id: int):
    eliminado = delete_reserva(reserva_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return JSONResponse(content={"mensaje": "Reserva eliminada exitosamente"}, status_code=200)


@app.get("/reservas/editar/{reserva_id}", response_class=HTMLResponse)
def get_editar_reserva(request: Request, reserva_id: int):
    reserva_data = fetch_reserva_by_id(reserva_id)
    if not reserva_data:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    reserva = ReservaDB(**reserva_data)
    clientes_rows = fetch_all_clientes()
    vehiculos_rows = fetch_all_vehiculos()
    clientes = map_rows_to_clientes(clientes_rows)
    vehiculos = map_rows_to_vehiculos(vehiculos_rows)
    return templates.TemplateResponse(
        "pages/editar_reserva.html",
        {"request": request, "reserva": reserva, "clientes": clientes, "vehiculos": vehiculos}
    )


@app.post("/reservas/editar/{reserva_id}")
def post_editar_reserva(
    request: Request,
    reserva_id: int,
    cliente_id: int = Form(...),
    vehiculo_id: int = Form(...),
    empleado_id: Optional[int] = Form(None),
    fecha_inicio: str = Form(...),
    fecha_fin: str = Form(...),
    estado: str = Form(...),
    total_estimado: Optional[float] = Form(None),
    notas: Optional[str] = Form(None)
):
    try:
        reserva_data = ReservaBase(
            cliente_id=cliente_id,
            vehiculo_id=vehiculo_id,
            empleado_id=empleado_id if empleado_id else None,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
            total_estimado=total_estimado if total_estimado is not None else None,
            notas=notas if notas else None
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
            reserva_data.notas
        )

        if not actualizado:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        return RedirectResponse(url="/reservas", status_code=303)

    except ValidationError as e:
        errores = []
        for error in e.errors():
            campo = str(error['loc'][0]) if error['loc'] else 'campo'
            mensaje = error['msg']
            errores.append(f"{campo.capitalize()}: {mensaje}")

        reserva_temp = ReservaDB(
            id=reserva_id,
            cliente_id=cliente_id,
            vehiculo_id=vehiculo_id,
            empleado_id=empleado_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
            total_estimado=total_estimado,
            notas=notas
        )

        clientes_rows = fetch_all_clientes()
        vehiculos_rows = fetch_all_vehiculos()
        clientes = map_rows_to_clientes(clientes_rows)
        vehiculos = map_rows_to_vehiculos(vehiculos_rows)

        return templates.TemplateResponse(
            "pages/editar_reserva.html",
            {"request": request, "reserva": reserva_temp, "errores": errores, "clientes": clientes, "vehiculos": vehiculos},
            status_code=422
        )


# ----------------------------
# Pagos (simple)
# ----------------------------
@app.post("/pagos/nuevo")
def post_nuevo_pago(
    reserva_id: int = Form(...),
    monto: float = Form(...),
    metodo_pago: str = Form(...),
    referencia: Optional[str] = Form(None)
):
    # Validaciones mínimas
    if monto <= 0:
        raise HTTPException(status_code=422, detail="Monto debe ser mayor que 0")

    pago_id = insert_pago(reserva_id, monto, metodo_pago, referencia)
    if not pago_id:
        raise HTTPException(status_code=400, detail="No se pudo registrar el pago")

    return JSONResponse(content={"mensaje": "Pago registrado", "pago_id": pago_id}, status_code=201)


@app.get("/pagos/{reserva_id}", response_class=JSONResponse)
def get_pagos_reserva(reserva_id: int):
    pagos = fetch_pagos_by_reserva(reserva_id)
    return JSONResponse(content={"pagos": pagos}, status_code=200)


# ----------------------------
# Mensajes de salud y fin
# ----------------------------
@app.get("/health", response_class=JSONResponse)
def health_check():
    return JSONResponse(content={"status": "ok", "service": "autorent"}, status_code=200)