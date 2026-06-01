-- ============================================================
-- EXOTIC MOTORS — Base de Datos
-- MariaDB / MySQL  |  DB: concesionario
-- ============================================================

CREATE DATABASE IF NOT EXISTS concesionario CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE concesionario;

-- ─── COCHES ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS coches (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    marca        VARCHAR(50)  NOT NULL,
    modelo       VARCHAR(100) NOT NULL,
    estado       VARCHAR(30)  DEFAULT 'Disponible',
    km           INT          DEFAULT 0,
    cambio       VARCHAR(30),
    precio       DECIMAL(12,2),
    motor        VARCHAR(100),
    aceleracion  VARCHAR(30),
    traccion     VARCHAR(30),
    img          VARCHAR(500)
) ENGINE=InnoDB;

-- ─── CLIENTES ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clientes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    dni             VARCHAR(20)  UNIQUE NOT NULL,
    telefono        VARCHAR(20),
    email           VARCHAR(150) UNIQUE,
    password        VARCHAR(255)
) ENGINE=InnoDB;

-- ─── EMPLEADOS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS empleados (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nombre_completo  VARCHAR(150) NOT NULL,
    email_corporativo VARCHAR(150) UNIQUE NOT NULL,
    password_hash    VARCHAR(255)
) ENGINE=InnoDB;

-- Datos iniciales de empleados (password en texto plano — cambiar en producción)
INSERT IGNORE INTO empleados (id, nombre_completo, email_corporativo, password_hash) VALUES
(1, 'Gerard Gonzalez',      'ggonzalez@exoticmotors.proven', 'Admin2026'),
(2, 'Oscar Ducuara Moreno', 'oducuara@exoticmotors.proven',  'Admin2026'),
(3, 'Juan Carlos Sa',       'jcarlos@exoticmotors.proven',   'Admin2026'),
(4, 'Joel Nieto',           'jnieto@exoticmotors.proven',    'Admin2026');

-- ─── RESERVAS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reservas (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    id_coche     INT NOT NULL,
    id_cliente   INT NOT NULL,
    id_empleado  INT,
    mensaje      TEXT,
    fecha        DATETIME DEFAULT CURRENT_TIMESTAMP,
    estado       VARCHAR(30) DEFAULT 'Pendiente',
    fecha_cita   DATETIME,
    FOREIGN KEY (id_coche)    REFERENCES coches(id),
    FOREIGN KEY (id_cliente)  REFERENCES clientes(id),
    FOREIGN KEY (id_empleado) REFERENCES empleados(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ─── USUARIO BD ───────────────────────────────────────────────
-- Ejecutar como root en MariaDB:
-- CREATE USER 'app_web'@'%' IDENTIFIED BY 'Web_P4ssw0rd_S3cur3!';
-- GRANT ALL PRIVILEGES ON concesionario.* TO 'app_web'@'%';
-- FLUSH PRIVILEGES;
