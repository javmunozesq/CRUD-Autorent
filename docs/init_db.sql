-- =========================================================
-- SCRIPT INICIALIZADOR DE BASE DE DATOS PARA EL PROYECTO AUTORENT
-- Autor: Generado por Copilot
-- Fecha: 2026-01-12
-- Descripción:
--   Este script elimina la base de datos si ya existe,
--   la crea desde cero y define las tablas necesarias para
--   un sistema de alquiler de coches (CRUD).
-- =========================================================

-- 1️⃣ Borrar la base de datos si ya existe
-- =========================================================
-- SCRIPT INICIALIZADOR DE BASE DE DATOS PARA EL PROYECTO AUTORENT (MariaDB)
-- Autor: Generado por Copilot (adaptado para MariaDB)
-- Fecha: 2026-01-12
-- Descripción:
--   Elimina la base de datos si existe, la crea y define tablas
--   para un sistema de alquiler de coches (clientes, vehiculos, modelos, categorias, reservas, pagos, empleados).
-- =========================================================

-- 1) Borrar la base de datos si ya existe
DROP DATABASE IF EXISTS autorent;

-- 2) Crear la base de datos
CREATE DATABASE IF NOT EXISTS autorent CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

-- 3) Seleccionar la base de datos
USE autorent;

-- 4) Tabla categorias
CREATE TABLE categorias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 5) Tabla modelos (marca y modelo). 'anio' en lugar de 'año' para compatibilidad.
CREATE TABLE modelos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    anio YEAR,
    categoria_id INT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_modelos_categoria FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 6) Tabla vehiculos
CREATE TABLE vehiculos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    matricula VARCHAR(20) NOT NULL UNIQUE,
    vin VARCHAR(50) UNIQUE,
    modelo_id INT NOT NULL,
    color VARCHAR(50),
    kilometraje INT DEFAULT 0,
    estado ENUM('disponible','alquilado','mantenimiento','reservado') NOT NULL DEFAULT 'disponible',
    precio_dia DECIMAL(10,2) NOT NULL,
    ubicacion VARCHAR(150),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_vehiculos_modelo FOREIGN KEY (modelo_id) REFERENCES modelos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 7) Tabla clientes
CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    telefono VARCHAR(50),
    direccion VARCHAR(255),
    dni_pasaporte VARCHAR(50) UNIQUE,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 8) Tabla empleados
CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    telefono VARCHAR(50),
    puesto VARCHAR(100),
    fecha_contratacion DATE,
    activo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 9) Tabla reservas
CREATE TABLE reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    vehiculo_id INT NOT NULL,
    empleado_id INT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    fecha_reserva TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado ENUM('pendiente','confirmada','en_curso','finalizada','cancelada') NOT NULL DEFAULT 'pendiente',
    total_estimado DECIMAL(10,2),
    notas TEXT,
    CONSTRAINT fk_reservas_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    CONSTRAINT fk_reservas_vehiculo FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id) ON DELETE RESTRICT,
    CONSTRAINT fk_reservas_empleado FOREIGN KEY (empleado_id) REFERENCES empleados(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 10) Tabla pagos
CREATE TABLE pagos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reserva_id INT NOT NULL,
    fecha_pago TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    monto DECIMAL(10,2) NOT NULL,
    metodo_pago ENUM('tarjeta','efectivo','transferencia','paypal') NOT NULL DEFAULT 'tarjeta',
    referencia VARCHAR(150),
    estado_pago ENUM('pendiente','completado','reembolsado') NOT NULL DEFAULT 'completado',
    CONSTRAINT fk_pagos_reserva FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 11) Índices útiles
CREATE INDEX idx_vehiculos_estado ON vehiculos(estado);
CREATE INDEX idx_reservas_estado ON reservas(estado);
CREATE INDEX idx_reservas_fechas ON reservas(fecha_inicio, fecha_fin);

-- 12) Datos de ejemplo para categorias
INSERT INTO categorias (nombre, descripcion) VALUES
('Económico', 'Vehículos pequeños y eficientes'),
('Compacto', 'Coches compactos para ciudad'),
('SUV', 'Vehículos todoterreno y familiares'),
('Lujo', 'Coches de alta gama');

-- 13) Datos de ejemplo para modelos
INSERT INTO modelos (marca, modelo, anio, categoria_id) VALUES
('Toyota', 'Corolla', 2020, 2),
('Renault', 'Clio', 2019, 1),
('Nissan', 'Qashqai', 2021, 3),
('BMW', 'Serie 5', 2022, 4);

-- 14) Datos de ejemplo para vehiculos
INSERT INTO vehiculos (matricula, vin, modelo_id, color, kilometraje, estado, precio_dia, ubicacion) VALUES
('1234ABC', 'VIN0001', 1, 'Blanco', 25000, 'disponible', 35.00, 'Madrid - Centro'),
('5678DEF', 'VIN0002', 2, 'Rojo', 40000, 'disponible', 28.50, 'Madrid - Aeropuerto'),
('9012GHI', 'VIN0003', 3, 'Negro', 15000, 'mantenimiento', 50.00, 'Taller Central'),
('3456JKL', 'VIN0004', 4, 'Azul', 10000, 'disponible', 120.00, 'Madrid - Centro');

-- 15) Datos de ejemplo para clientes
INSERT INTO clientes (nombre, apellido, email, telefono, direccion, dni_pasaporte) VALUES
('Juan', 'Pérez', 'juan.perez@example.com', '600111222', 'Calle Falsa 1, Madrid', 'X1234567A'),
('María', 'García', 'maria.garcia@example.com', '600333444', 'Avenida Real 5, Madrid', 'Y7654321B');

-- 16) Datos de ejemplo para empleados
INSERT INTO empleados (nombre, apellido, email, telefono, puesto, fecha_contratacion) VALUES
('Laura', 'Sánchez', 'laura.sanchez@autorent.com', '610111222', 'Atención al cliente', '2023-06-01'),
('Pedro', 'Martín', 'pedro.martin@autorent.com', '610333444', 'Encargado flota', '2022-03-15');

-- 17) Ejemplo de reserva y pago asociado
INSERT INTO reservas (cliente_id, vehiculo_id, empleado_id, fecha_inicio, fecha_fin, estado, total_estimado, notas) VALUES
(1, 1, 1, '2026-02-01 10:00:00', '2026-02-05 10:00:00', 'confirmada', 140.00, 'Recoger en oficina central');

-- Usar LAST_INSERT_ID() inmediatamente después del INSERT anterior para asociar el pago
INSERT INTO pagos (reserva_id, fecha_pago, monto, metodo_pago, referencia, estado_pago) VALUES
(LAST_INSERT_ID(), NOW(), 140.00, 'tarjeta', 'TXN123456', 'completado');

-- 18) Consultas de verificación
SELECT COUNT(*) AS total_categorias FROM categorias;
SELECT * FROM modelos LIMIT 10;
SELECT * FROM vehiculos LIMIT 10;
SELECT * FROM clientes LIMIT 10;

SELECT r.id, c.nombre, c.apellido, v.matricula, r.fecha_inicio, r.fecha_fin, r.estado
FROM reservas r
JOIN clientes c ON r.cliente_id = c.id
JOIN vehiculos v ON r.vehiculo_id = v.id
LIMIT 20;

-- Fin del script