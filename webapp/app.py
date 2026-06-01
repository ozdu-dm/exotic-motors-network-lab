from flask import Flask, render_template, request, redirect, url_for, session, Response
from fpdf import FPDF
import smtplib
import os
import db_module

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-only-change-in-production')


# ─── RUTAS PÚBLICAS ───────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/inventario")
def inventario():
    marca_filtro = request.args.get('marca')
    estado_filtro = request.args.get('estado')

    if marca_filtro:
        lista_coches = db_module.obtener_coches_por_marca(marca_filtro)
    elif estado_filtro == '0KM':
        lista_coches = db_module.obtener_coches_0km()
    else:
        lista_coches = db_module.obtener_coches()

    return render_template("inventario.html", coches=lista_coches)


@app.route("/coche/<int:id_coche>")
def detalle_coche(id_coche):
    coche = db_module.obtener_coche_por_id(id_coche)
    if not coche:
        return "Vehículo no encontrado", 404
    return render_template("detalle.html", coche=coche)


# ─── AUTENTICACIÓN CLIENTES ───────────────────────────────────────────────────

@app.route("/registro", methods=['GET', 'POST'])
def registro():
    next_url = request.args.get('next') or request.form.get('next') or ''
    if not next_url.startswith('/'):
        next_url = ''

    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        dni      = request.form.get('dni', '').strip()
        telefono = request.form.get('telefono', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        import re
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return render_template("registro.html",
                                   error="El email no tiene un formato válido.", next=next_url)
        if len(password) < 8 or not any(c.isdigit() for c in password):
            return render_template("registro.html",
                                   error="La contraseña necesita mínimo 8 caracteres y al menos 1 número.",
                                   next=next_url)

        exito = db_module.registrar_cliente(nombre, dni, telefono, email, password)
        if exito:
            login_url = url_for('login_cliente')
            if next_url:
                login_url += f'?next={next_url}'
            return redirect(login_url)
        else:
            return render_template("registro.html",
                                   error="El DNI o email ya están registrados.", next=next_url)

    return render_template("registro.html", next=next_url)


@app.route("/login_cliente", methods=['GET', 'POST'])
def login_cliente():
    next_url = request.args.get('next') or request.form.get('next') or ''
    if not next_url.startswith('/'):
        next_url = ''

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        cliente = db_module.validar_cliente_por_email(email, password)
        if cliente:
            session['cliente_dni']    = cliente['dni']
            session['cliente_nombre'] = cliente['nombre_completo']
            return redirect(next_url or url_for('mis_reservas'))
        else:
            return render_template("login_cliente.html",
                                   error="Email o contraseña incorrectos.", next=next_url)

    return render_template("login_cliente.html", next=next_url)


@app.route("/logout_cliente")
def logout_cliente():
    session.pop('cliente_dni', None)
    session.pop('cliente_nombre', None)
    return redirect(url_for('login_cliente'))


# ─── ZONA CLIENTES (requiere login) ──────────────────────────────────────────

@app.route("/reserva/<int:id_coche>", methods=['GET', 'POST'])
def reserva(id_coche):
    if 'cliente_dni' not in session:
        return redirect(url_for('login_cliente', next=f'/reserva/{id_coche}'))

    coche = db_module.obtener_coche_por_id(id_coche)

    if request.method == 'POST':
        nombre   = session['cliente_nombre']
        dni      = session['cliente_dni']
        telefono = request.form.get('telefono', '')
        mensaje  = request.form.get('mensaje', '')

        exito = db_module.procesar_reserva_completa(id_coche, nombre, dni, telefono, mensaje)
        if exito:
            return redirect(url_for('mis_reservas'))
        else:
            return "Error interno al procesar la reserva.", 500

    return render_template("reserva.html", coche=coche,
                           nombre_vip=session['cliente_nombre'],
                           dni_vip=session['cliente_dni'])


@app.route("/mis_reservas")
def mis_reservas():
    if 'cliente_dni' not in session:
        return redirect(url_for('login_cliente'))

    dni_seguro = session['cliente_dni']
    datos_crudos = db_module.obtener_reservas_por_dni(dni_seguro)

    lista_reservas = []
    for r in datos_crudos:
        if isinstance(r, dict):
            lista_reservas.append(r)
        else:
            lista_reservas.append({
                'id': r[0], 'id_cliente': r[1], 'id_coche': r[2],
                'mensaje': r[3], 'estado': r[4], 'fecha': r[5],
                'comercial': r[6] if len(r) > 6 else None,
                'fecha_cita': r[7] if len(r) > 7 else None,
                'marca': r[8] if len(r) > 8 else "Vehículo",
                'modelo': r[9] if len(r) > 9 else "Exótico",
                'precio': r[10] if len(r) > 10 else 0,
                'img': r[11] if len(r) > 11 else ""
            })

    return render_template("mis_reservas.html", reservas=lista_reservas)


@app.route("/descargar_certificado/<int:id_reserva>")
def descargar_certificado(id_reserva):
    if 'cliente_dni' not in session:
        return redirect(url_for('login_cliente'))

    reserva = db_module.obtener_reserva_por_id(id_reserva)
    if not reserva:
        return "Reserva no encontrada", 404

    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(20, 20, 20)

        pdf.set_draw_color(212, 175, 55)
        pdf.set_linewidth(1.5)
        pdf.rect(10, 10, 190, 277)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 26)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(170, 15, "EXOTICS MOTORS", ln=True, align="C")

        pdf.set_font("Arial", "I", 10)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(170, 5, "CONCESIONARIO OFICIAL DE ALTA GAMA", ln=True, align="C")

        pdf.ln(10)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(30, 55, 180, 55)

        pdf.ln(15)
        pdf.set_font("Arial", "B", 16)
        pdf.set_text_color(212, 175, 55)
        pdf.cell(170, 10, "CERTIFICADO DE SOLICITUD VIP", ln=True, align="C")
        pdf.ln(10)

        pdf.set_fill_color(245, 245, 245)
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(170, 10, "  INFORMACION DEL TITULAR", ln=True, fill=True)

        pdf.set_font("Arial", "", 11)
        nombre_cliente = session.get('cliente_nombre', 'Cliente VIP').encode('latin-1', 'replace').decode('latin-1')
        pdf.ln(2)
        pdf.cell(170, 8, f"   Nombre del Solicitante: {nombre_cliente}", ln=True)
        pdf.cell(170, 8, f"   Identificador de Cliente: {session.get('cliente_dni', 'N/A')}", ln=True)

        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(170, 10, "  DETALLES DEL SUPERDEPORTIVO", ln=True, fill=True)

        pdf.set_font("Arial", "", 11)
        marca  = str(reserva['marca']).encode('latin-1', 'replace').decode('latin-1')
        modelo = str(reserva['modelo']).encode('latin-1', 'replace').decode('latin-1')
        estado = str(reserva['estado']).encode('latin-1', 'replace').decode('latin-1')

        try:
            precio_formateado = "{:,.2f}".format(float(reserva['precio'])).replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            precio_formateado = "Consultar"

        pdf.ln(2)
        pdf.cell(170, 8, f"   Vehiculo: {marca} {modelo}", ln=True)
        pdf.cell(170, 8, f"   Precio de Lista: {precio_formateado} EUR", ln=True)
        pdf.cell(170, 8, f"   Estado de la Solicitud: {estado.upper()}", ln=True)
        pdf.cell(170, 8, f"   Referencia Interna: #EX-{id_reserva:05d}", ln=True)

        pdf.ln(20)
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(150, 150, 150)
        pdf.multi_cell(170, 5,
                       "Este documento certifica que la solicitud de reserva ha sido procesada "
                       "correctamente en nuestro sistema central. La adjudicacion final queda sujeta "
                       "a la confirmacion por parte de un asesor comercial de Exotics Motors.",
                       align="C")

        pdf.ln(15)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(212, 175, 55)
        pdf.cell(170, 5, "DOCUMENTO FIRMADO DIGITALMENTE", ln=True, align="R")
        pdf.set_font("Arial", "", 8)
        pdf.cell(170, 5, f"Verificacion: security.exoticsmotors.com/verify/{id_reserva}x99", ln=True, align="R")

        pdf_bytes = bytes(pdf.output(dest='S'))

        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Certificado_VIP_{id_reserva}.pdf",
                "Content-Length": str(len(pdf_bytes))
            }
        )
    except Exception as e:
        return f"Error al generar PDF: {e}", 500


# ─── AUTENTICACIÓN EMPLEADOS ──────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form['usuario']
        password = request.form['password']

        empleado = db_module.obtener_empleado_por_email(email)

        if empleado and empleado['password_hash'] == password:
            session['admin_vip']       = True
            session['id_empleado']     = empleado['id']
            session['nombre_empleado'] = empleado['nombre_completo']
            return redirect(url_for('admin'))
        else:
            error = "Email corporativo o contraseña incorrectos."

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('admin_vip', None)
    return redirect(url_for('home'))


# ─── ZONA ADMIN (requiere login empleado) ─────────────────────────────────────

@app.route("/admin")
def admin():
    if not session.get('admin_vip'):
        return redirect(url_for('login'))
    lista_reservas = db_module.obtener_reservas_admin()
    return render_template("admin.html", reservas=lista_reservas)


@app.route('/asignar_reserva/<int:id_reserva>', methods=['POST'])
def asignar_reserva(id_reserva):
    if not session.get('admin_vip'):
        return redirect(url_for('login'))

    id_empleado = session.get('id_empleado')
    fecha_cita  = request.form.get('fecha_cita', '').strip()
    fecha_cita  = fecha_cita.replace('T', ' ') if fecha_cita else None

    db_module.asignar_empleado_a_reserva(id_reserva, id_empleado, fecha_cita)
    notificar_vendedor(id_reserva, id_empleado)

    return redirect(url_for('admin'))


@app.route('/actualizar_estado', methods=['POST'])
def actualizar_estado():
    if not session.get('admin_vip'):
        return redirect(url_for('login'))

    reserva_id   = request.form.get('reserva_id')
    nuevo_estado = request.form.get('estado')
    fecha_cita   = request.form.get('fecha_cita')

    if not reserva_id or reserva_id.strip() == '':
        return redirect(url_for('admin'))

    if not fecha_cita or fecha_cita.strip() == '':
        fecha_cita = None
    else:
        fecha_cita = fecha_cita.replace('T', ' ')

    db_module.actualizar_estado(reserva_id, nuevo_estado, fecha_cita)
    return redirect(url_for('admin'))


# ─── NOTIFICACIÓN EMAIL AL VENDEDOR ──────────────────────────────────────────

def notificar_vendedor(id_reserva, id_empleado):
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', '10.0.10.10'),
            user=os.environ.get('DB_USER', 'app_web'),
            password=os.environ.get('DB_PASSWORD', ''),
            database=os.environ.get('DB_NAME', 'concesionario')
        )
        cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT e.nombre_completo  AS empleado,
                   e.email_corporativo,
                   cl.nombre_completo AS cliente,
                   cl.telefono,
                   co.marca, co.modelo,
                   r.fecha_cita
            FROM reservas r
            JOIN clientes  cl ON r.id_cliente = cl.id
            JOIN coches    co ON r.id_coche   = co.id
            JOIN empleados e  ON e.id         = %s
            WHERE r.id = %s
        """, (id_empleado, id_reserva))
        datos = cur.fetchone()
        conn.close()

        if not datos:
            return

        fecha  = datos['fecha_cita'].strftime('%d/%m/%Y  %H:%M') if datos['fecha_cita'] else 'Por confirmar'
        asunto = f"Visita asignada — {datos['cliente']} | {datos['marca']} {datos['modelo']}"
        cuerpo = (
            f"Hola {datos['empleado']},\r\n\r\n"
            f"Se te ha asignado la siguiente visita en EXOTIC MOTORS:\r\n\r\n"
            f"  Cliente   : {datos['cliente']}\r\n"
            f"  Telefono  : {datos['telefono'] or 'no indicado'}\r\n"
            f"  Vehiculo  : {datos['marca']} {datos['modelo']}\r\n"
            f"  Fecha/Hora: {fecha}\r\n\r\n"
            f"Accede al panel para gestionar el estado de la visita.\r\n\r\n"
            f"EXOTIC MOTORS\r\n"
        )
        mail_from = os.environ.get('MAIL_FROM', 'noreply@exoticmotors.proven')
        mensaje = (
            f"From: {mail_from}\r\n"
            f"To: {datos['email_corporativo']}\r\n"
            f"Subject: {asunto}\r\n\r\n"
            f"{cuerpo}"
        )
        mail_host = os.environ.get('MAIL_HOST', '10.0.87.11')
        mail_port = int(os.environ.get('MAIL_PORT', '25'))
        s = smtplib.SMTP(mail_host, mail_port, timeout=30)
        s.sendmail(mail_from, [datos['email_corporativo']], mensaje)
        s.quit()
    except Exception as e:
        print(f"[notificar_vendedor] Error: {e}")


if __name__ == "__main__":
    app.run(debug=True)
