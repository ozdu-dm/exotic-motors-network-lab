import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash


def conectar():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', '10.0.10.10'),
        user=os.environ.get('DB_USER', 'app_web'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'concesionario')
    )


# ─── COCHES ──────────────────────────────────────────────────────────────────

def obtener_coches():
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM coches ORDER BY marca, modelo")
    result = cur.fetchall()
    conn.close()
    return result


def obtener_coches_por_marca(marca):
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM coches WHERE marca = %s ORDER BY modelo", (marca,))
    result = cur.fetchall()
    conn.close()
    return result


def obtener_coches_0km():
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM coches WHERE estado = '0KM' ORDER BY marca, modelo")
    result = cur.fetchall()
    conn.close()
    return result


def obtener_coche_por_id(id_coche):
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM coches WHERE id = %s", (id_coche,))
    result = cur.fetchone()
    conn.close()
    return result


# ─── CLIENTES ─────────────────────────────────────────────────────────────────

def registrar_cliente(nombre, dni, telefono, email, password):
    try:
        conn = conectar()
        cur = conn.cursor()
        hashed = generate_password_hash(password)
        sql = "INSERT INTO clientes (nombre_completo, dni, telefono, email, password) VALUES (%s, %s, %s, %s, %s)"
        cur.execute(sql, (nombre, dni, telefono, email, hashed))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def validar_cliente_por_email(email, password):
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM clientes WHERE email = %s", (email,))
    user = cur.fetchone()
    conn.close()
    if user and check_password_hash(user['password'], password):
        return user
    return None


# ─── EMPLEADOS ───────────────────────────────────────────────────────────────

def obtener_empleado_por_email(email):
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM empleados WHERE email_corporativo = %s", (email,))
    result = cur.fetchone()
    conn.close()
    return result


# ─── RESERVAS ─────────────────────────────────────────────────────────────────

def procesar_reserva_completa(id_coche, nombre, dni, telefono, mensaje):
    try:
        conn = conectar()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM clientes WHERE dni = %s", (dni,))
        cliente = cur.fetchone()
        if not cliente:
            conn.close()
            return False
        id_cliente = cliente['id']
        cur.execute(
            "INSERT INTO reservas (id_coche, id_cliente, mensaje, estado) VALUES (%s, %s, %s, 'pendiente')",
            (id_coche, id_cliente, mensaje)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def obtener_reservas_por_dni(dni):
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.id, r.id_cliente, r.id_coche, r.mensaje, r.estado, r.fecha,
               e.nombre_completo AS comercial, r.fecha_cita,
               c.marca, c.modelo, c.precio, c.img
        FROM reservas r
        JOIN coches c ON r.id_coche = c.id
        JOIN clientes cl ON r.id_cliente = cl.id
        LEFT JOIN empleados e ON r.id_empleado = e.id
        WHERE cl.dni = %s
        ORDER BY r.fecha DESC
    """, (dni,))
    result = cur.fetchall()
    conn.close()
    return result


def obtener_reservas_admin():
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.id, r.estado, r.fecha, r.fecha_cita, r.mensaje,
               cl.nombre_completo AS cliente, cl.telefono,
               co.marca, co.modelo, co.precio,
               e.nombre_completo AS empleado, e.email_corporativo
        FROM reservas r
        JOIN clientes cl ON r.id_cliente = cl.id
        JOIN coches co ON r.id_coche = co.id
        LEFT JOIN empleados e ON r.id_empleado = e.id
        ORDER BY r.fecha DESC
    """)
    result = cur.fetchall()
    conn.close()
    return result


def obtener_reserva_por_id(id_reserva):
    conn = conectar()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.*, c.marca, c.modelo, c.precio
        FROM reservas r
        JOIN coches c ON r.id_coche = c.id
        WHERE r.id = %s
    """, (id_reserva,))
    result = cur.fetchone()
    conn.close()
    return result


def asignar_empleado_a_reserva(id_reserva, id_empleado, fecha_cita):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "UPDATE reservas SET id_empleado = %s, fecha_cita = %s, estado = 'confirmada' WHERE id = %s",
        (id_empleado, fecha_cita, id_reserva)
    )
    conn.commit()
    conn.close()


def actualizar_estado(id_reserva, nuevo_estado, fecha_cita):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "UPDATE reservas SET estado = %s, fecha_cita = %s WHERE id = %s",
        (nuevo_estado, fecha_cita, id_reserva)
    )
    conn.commit()
    conn.close()
