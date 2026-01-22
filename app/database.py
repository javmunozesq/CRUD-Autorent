# app/database.py
from dotenv import load_dotenv, find_dotenv
import os
import mysql.connector
from mysql.connector import Error as MySQLError
from typing import List, Dict, Any, Optional, cast
from mysql.connector.cursor import MySQLCursorDict

# Carga .env desde la raíz del proyecto
load_dotenv(find_dotenv())


class DatabaseConnectionError(Exception):
    """
    Excepción personalizada para errores de conexión a la base de datos.
    Las rutas pueden capturar esta excepción y devolver una página de error amigable.
    """
    pass


def get_connection():
    """
    Crea y retorna una conexión a la base de datos MySQL/MariaDB
    usando variables de entorno. Valores por defecto pensados para
    un entorno de desarrollo local.

    Si falla la conexión, lanza DatabaseConnectionError con el mensaje original.
    """
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    # Compatibilidad con DB_PASSWORD o DB_PASS
    password = os.getenv("DB_PASSWORD", os.getenv("DB_PASS", ""))
    database = os.getenv("DB_NAME", "autorent")
    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except Exception:
        port = 3306

    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset="utf8mb4",
            use_unicode=True,
            autocommit=False,
            connection_timeout=5
        )
        return conn
    except MySQLError as e:
        # Lanzar excepción personalizada para que la app la maneje y muestre la plantilla de error
        raise DatabaseConnectionError(f"Error al conectar con la base de datos: {e}") from e
    except Exception as e:
        # Capturar cualquier otra excepción inesperada
        raise DatabaseConnectionError(f"Error inesperado al conectar con la base de datos: {e}") from e


# ----------------------------
# Clientes
# ----------------------------
def fetch_all_clientes() -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                "SELECT id, nombre, apellido, email, telefono, direccion FROM clientes ORDER BY id DESC;"
            )
            rows = cast(List[Dict[str, Any]], cur.fetchall())
            return rows
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def insert_cliente(
    nombre: str,
    apellido: str,
    email: str,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None
) -> int:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO clientes (nombre, apellido, email, telefono, direccion)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (nombre, apellido, email, telefono, direccion)
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def delete_cliente(cliente_id: int) -> bool:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def fetch_cliente_by_id(cliente_id: int) -> Optional[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                "SELECT id, nombre, apellido, email, telefono, direccion FROM clientes WHERE id = %s",
                (cliente_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def update_cliente(
    cliente_id: int,
    nombre: str,
    apellido: str,
    email: str,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE clientes
                SET nombre = %s, apellido = %s, email = %s, telefono = %s, direccion = %s
                WHERE id = %s
                """,
                (nombre, apellido, email, telefono, direccion, cliente_id)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


# ----------------------------
# Modelos y Categorías
# ----------------------------
def fetch_all_modelos() -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                "SELECT id, marca, modelo, anio, categoria_id FROM modelos ORDER BY marca, modelo;"
            )
            rows = cast(List[Dict[str, Any]], cur.fetchall())
            return rows
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def fetch_all_categorias() -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute("SELECT id, nombre, descripcion FROM categorias ORDER BY nombre;")
            rows = cast(List[Dict[str, Any]], cur.fetchall())
            return rows
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


# ----------------------------
# Vehículos
# ----------------------------
def fetch_all_vehiculos() -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                """
                SELECT v.id, v.matricula, v.vin, v.modelo_id, v.color, v.kilometraje,
                       v.estado, v.precio_dia, v.ubicacion, m.marca, m.modelo AS modelo_nombre
                FROM vehiculos v
                LEFT JOIN modelos m ON v.modelo_id = m.id
                ORDER BY v.id DESC;
                """
            )
            rows = cast(List[Dict[str, Any]], cur.fetchall())
            return rows
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def insert_vehiculo(
    matricula: str,
    vin: Optional[str],
    modelo_id: int,
    color: Optional[str],
    kilometraje: int,
    estado: str,
    precio_dia: float,
    ubicacion: Optional[str]
) -> int:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO vehiculos (matricula, vin, modelo_id, color, kilometraje, estado, precio_dia, ubicacion)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (matricula, vin, modelo_id, color, kilometraje, estado, precio_dia, ubicacion)
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def delete_vehiculo(vehiculo_id: int) -> bool:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM vehiculos WHERE id = %s", (vehiculo_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def fetch_vehiculo_by_id(vehiculo_id: int) -> Optional[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                """
                SELECT id, matricula, vin, modelo_id, color, kilometraje, estado, precio_dia, ubicacion
                FROM vehiculos WHERE id = %s
                """,
                (vehiculo_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def update_vehiculo(
    vehiculo_id: int,
    matricula: str,
    vin: Optional[str],
    modelo_id: int,
    color: Optional[str],
    kilometraje: int,
    estado: str,
    precio_dia: float,
    ubicacion: Optional[str]
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE vehiculos
                SET matricula = %s, vin = %s, modelo_id = %s, color = %s,
                    kilometraje = %s, estado = %s, precio_dia = %s, ubicacion = %s
                WHERE id = %s
                """,
                (matricula, vin, modelo_id, color, kilometraje, estado, precio_dia, ubicacion, vehiculo_id)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


# ----------------------------
# Reservas
# ----------------------------
def fetch_all_reservas() -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                """
                SELECT r.id, r.cliente_id, r.vehiculo_id, r.empleado_id,
                       r.fecha_inicio, r.fecha_fin, r.fecha_reserva, r.estado, r.total_estimado, r.notas,
                       c.nombre AS cliente_nombre, c.apellido AS cliente_apellido,
                       v.matricula AS vehiculo_matricula
                FROM reservas r
                LEFT JOIN clientes c ON r.cliente_id = c.id
                LEFT JOIN vehiculos v ON r.vehiculo_id = v.id
                ORDER BY r.fecha_reserva DESC;
                """
            )
            rows = cast(List[Dict[str, Any]], cur.fetchall())
            return rows
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def insert_reserva(
    cliente_id: int,
    vehiculo_id: int,
    empleado_id: Optional[int],
    fecha_inicio: str,
    fecha_fin: str,
    estado: str,
    total_estimado: Optional[float],
    notas: Optional[str]
) -> int:
    """
    Inserta una reserva y retorna el id insertado.
    Nota: no se realizan comprobaciones de disponibilidad aquí; la lógica de negocio
    debe implementarse en un nivel superior si se requiere.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO reservas (cliente_id, vehiculo_id, empleado_id, fecha_inicio, fecha_fin, fecha_reserva, estado, total_estimado, notas)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s)
                """,
                (cliente_id, vehiculo_id, empleado_id, fecha_inicio, fecha_fin, estado, total_estimado, notas)
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def delete_reserva(reserva_id: int) -> bool:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM reservas WHERE id = %s", (reserva_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def fetch_reserva_by_id(reserva_id: int) -> Optional[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                """
                SELECT id, cliente_id, vehiculo_id, empleado_id, fecha_inicio, fecha_fin, fecha_reserva, estado, total_estimado, notas
                FROM reservas WHERE id = %s
                """,
                (reserva_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def update_reserva(
    reserva_id: int,
    cliente_id: int,
    vehiculo_id: int,
    empleado_id: Optional[int],
    fecha_inicio: str,
    fecha_fin: str,
    estado: str,
    total_estimado: Optional[float],
    notas: Optional[str]
) -> bool:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE reservas
                SET cliente_id = %s, vehiculo_id = %s, empleado_id = %s,
                    fecha_inicio = %s, fecha_fin = %s, estado = %s, total_estimado = %s, notas = %s
                WHERE id = %s
                """,
                (cliente_id, vehiculo_id, empleado_id, fecha_inicio, fecha_fin, estado, total_estimado, notas, reserva_id)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


# ----------------------------
# Pagos
# ----------------------------
def insert_pago(
    reserva_id: int,
    monto: float,
    metodo_pago: str,
    referencia: Optional[str] = None
) -> int:
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO pagos (reserva_id, fecha_pago, monto, metodo_pago, referencia, estado_pago)
                VALUES (%s, NOW(), %s, %s, %s, 'completado')
                """,
                (reserva_id, monto, metodo_pago, referencia)
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()


def fetch_pagos_by_reserva(reserva_id: int) -> List[Dict[str, Any]]:
    conn = None
    try:
        conn = get_connection()
        cur: MySQLCursorDict = conn.cursor(dictionary=True)  # type: ignore[assignment]
        try:
            cur.execute(
                "SELECT id, reserva_id, fecha_pago, monto, metodo_pago, referencia, estado_pago FROM pagos WHERE reserva_id = %s ORDER BY fecha_pago DESC",
                (reserva_id,)
            )
            rows = cast(List[Dict[str, Any]], cur.fetchall())
            return rows
        finally:
            cur.close()
    finally:
        if conn:
            conn.close()