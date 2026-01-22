# app/controllers/__init__.py
# Este archivo permite importar los routers desde app.controllers
from .clientes import router as clientes_router
from .vehiculos import router as vehiculos_router
from .reservas import router as reservas_router
from .pagos import router as pagos_router

__all__ = ["clientes_router", "vehiculos_router", "reservas_router", "pagos_router"]