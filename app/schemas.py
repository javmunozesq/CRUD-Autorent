# app/schemas.py
from pydantic import BaseModel, EmailStr, field_validator, ValidationError
from typing import Optional, List, Any
import re

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

class ClienteDB(ClienteBase):
    id: int

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
    fecha_inicio: str
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

# Utilities to convert models to plain dicts for templates
def model_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return obj

def list_models_to_dicts(items: List[Any]) -> List[Any]:
    return [model_to_dict(i) for i in items]