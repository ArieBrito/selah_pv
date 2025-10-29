# -*- coding: utf-8 -*-
"""
TPV Dinámico (versión Streamlit)
Autor: Arie Brito
Actualizado: 27 octubre 2025
"""

import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from decimal import Decimal, InvalidOperation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="SELAH TPV", layout="wide")

PRIMARY_COLOR = '#A2D5B0'
ACCENT_COLOR = '#F6A441'
LOGO_PATH = "./www/logo.png"

# --- FUNCIÓN DE CONEXIÓN MYSQL ---
def conectar_db():
    try:
        conexion = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            connect_timeout=10  # evita cuelgues
        )

        if conexion.is_connected():
            st.session_state["db_ok"] = True
            return conexion
        else:
            st.session_state["db_ok"] = False
            st.error("❌ No se pudo establecer conexión con la base de datos.")
            return None

    except Error as e:
        st.session_state["db_ok"] = False
        st.error(f"⚠️ Error de conexión con la base de datos: {e}")
        return None


# --- OBTENER CLIENTES ---
def obtener_clientes():
    try:
        conexion = conectar_db()
        if not conexion:
            return []
        cursor = conexion.cursor()
        cursor.execute("SELECT ID_CLIENTE, NOMBRE_CLIENTE, APELLIDO_CLIENTE FROM CLIENTES")
        result = cursor.fetchall()
        cursor.close()
        conexion.close()
        return [(r[0], f"{r[1]} {r[2]}") for r in result]

    except Error as e:
        st.error(f"⚠️ Error al obtener clientes: {e}")
        return []

# --- OBTENER PRODUCTOS ---
def obtener_pulseras():
    try:
        conexion = conectar_db()
        if not conexion:
            return [('0000', 'Otro/Manual', 'M', Decimal('0.00'))]
        cursor = conexion.cursor()
        cursor.execute("SELECT ID_PRODUCTO, DESCRIPCION, CLASIFICACION, PRECIO_CLASIFICADO FROM PULSERAS")
        productos_db = cursor.fetchall()
        cursor.close()
        conexion.close()
        productos_db.append(('0000', 'Otro/Manual', 'M', Decimal('0.00')))
        return productos_db

    except Error as e:
        st.error(f"⚠️ Error al obtener pulseras: {e}")
        return [('0000', 'Otro/Manual', 'M', Decimal('0.00'))]

# --- GENERAR TICKET PDF ---
def generar_ticket(id_venta, cliente_nombre, productos, subtotal, descuento, total, pago, cambio, tipo_pago):
    carpeta_tickets = "tickets"
    os.makedirs(carpeta_tickets, exist_ok=True)
    archivo_pdf = os.path.join(carpeta_tickets, f"ticket_{id_venta}.pdf")

    c = canvas.Canvas(archivo_pdf, pagesize=letter)
    width, height = letter
    x_start = 50
    y = height - 100

    # --- Logo centrado ---
    logo_width = 100
    if os.path.exists(LOGO_PATH):
        x_logo = (width - logo_width) / 2
        c.drawImage(LOGO_PATH, x=x_logo, y=height-120, width=logo_width, preserveAspectRatio=True, mask='auto')

    # --- Título ---
    c.setFont("Helvetica-Bold", 16)
    y_title = height - 140  # ajusta según altura del logo
    c.drawCentredString(width / 2, y_title, "SELAH - TICKET DE VENTA")
    y = y_title - 30

    # --- Detalles del ticket ---
    c.setFont("Helvetica", 10)
    c.drawString(x_start, y, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.drawString(x_start, y, f"Cliente: {cliente_nombre}")
    y -= 25

    # --- Encabezados de productos ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_start, y, "Producto")
    c.drawString(250, y, "Cant.")
    c.drawString(350, y, "Precio")
    c.drawString(450, y, "Subtotal")
    y -= 10
    c.line(x_start, y, 550, y)
    y -= 15

    # --- Productos ---
    c.setFont("Helvetica", 10)
    for p in productos:
        c.drawString(x_start, y, p["desc"][:25])
        c.drawString(250, y, str(p["cant"]))
        c.drawRightString(400, y, f"${p['precio']:.2f}")
        c.drawRightString(550, y, f"${p['subtotal']:.2f}")
        y -= 15

    y -= 10
    c.line(x_start, y, 550, y)
    y -= 20

    # --- Totales ---
    c.drawRightString(470, y, "SUBTOTAL:")
    c.drawRightString(550, y, f"${subtotal:.2f}")
    y -= 15
    if descuento > 0:
        c.drawRightString(470, y, f"DESCUENTO ({descuento:.1f}%):")
        c.drawRightString(550, y, f"-${subtotal*(descuento/100):.2f}")
        y -= 15

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(470, y, "TOTAL:")
    c.drawRightString(550, y, f"${total:.2f}")
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawRightString(550, y, f"RECIBIDO: ${pago:.2f}")
    y -= 15

    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(550, y, f"CAMBIO: ${cambio:.2f}")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(x_start, y, f"Tipo de pago: {tipo_pago}")
    y -= 40

    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width / 2, y, "¡Gracias por su compra!")

    c.save()
    return archivo_pdf
    
# --- INTERFAZ PRINCIPAL ---
st.title("Selah TPV")
st.markdown("---")

clientes = obtener_clientes()
productos = obtener_pulseras()

col1, col2 = st.columns(2)

# --- CLIENTE ---
with col1:
    st.subheader("👤 Información del Cliente")
    opciones_clientes = [f"{c[0]} - {c[1]}" for c in clientes]
    cliente_sel = st.selectbox("Cliente registrado:", opciones_clientes)
    cliente_otro = st.text_input("Cliente (otro):")
    nuevo = st.checkbox("Registrar nuevo cliente")
    if nuevo:
        with st.form("nuevo_cliente"):
            nombre = st.text_input("Nombre")
            apellido = st.text_input("Apellido")
            edad = st.number_input("Edad", min_value=0, max_value=120, step=1)
            correo = st.text_input("Correo")
            telefono = st.text_input("Teléfono")
            direccion = st.text_area("Dirección")
            preferente = st.checkbox("Cliente preferente")
            promos = st.checkbox("Recibe promociones", value=True)
            if st.form_submit_button("Guardar"):
                conexion = conectar_db()
                if conexion:
                    cursor = conexion.cursor()
                    sql = """INSERT INTO CLIENTES (NOMBRE_CLIENTE, APELLIDO_CLIENTE, EDAD, CORREO, TELEFONO, DIRECCION, PREFERENTE, PROMOS)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
                    datos = (nombre, apellido, edad, correo, telefono, direccion, preferente, promos)
                    cursor.execute(sql, datos)
                    conexion.commit()
                    st.success("Cliente registrado correctamente.")
                    cursor.close()
                    conexion.close()
                    st.cache_data.clear()


# --- PRODUCTOS ---
with col2:
    st.subheader("📦 Productos de la Venta")
    num_productos = st.number_input("Número de productos", min_value=1, max_value=20, value=1, step=1)

    lista_venta = []
    total = Decimal('0')
    for i in range(num_productos):
        st.markdown(f"**Producto #{i+1}**")
        colp1, colp2, colp3 = st.columns([3, 1, 1])
        id_prod = colp1.selectbox(f"Producto {i+1}", [p[0] for p in productos], key=f"prod_{i}")
        cant = colp2.number_input("Cant.", min_value=1, value=1, key=f"cant_{i}")
        if id_prod == '0000':
            precio = Decimal(str(colp3.number_input("Precio manual", min_value=0.0, value=0.0, key=f"precio_manual_{i}")))
            desc = "Manual"
        else:
            prod_sel = next((p for p in productos if p[0] == id_prod), None)
            precio = Decimal(str(prod_sel[3])) if prod_sel else Decimal('0.00')
            desc = prod_sel[1] if prod_sel else ""
            colp3.write(f"💰 ${precio}")
        subtotal = precio * cant
        total += subtotal
        lista_venta.append({"id_producto": id_prod, "desc": desc, "cant": cant, "precio": precio, "subtotal": subtotal})
    st.info(f"Subtotal sin descuento: ${total:.2f}")

# --- PAGO ---
st.subheader("💳 Detalles de Pago")
colp1, colp2, colp3, colp4 = st.columns(4)

descuento = Decimal(str(colp1.number_input("Descuento (%)", min_value=0.0, max_value=30.0, step=0.5)))
tipo_venta = colp2.selectbox("Tipo de venta", ["Contado", "A cuenta", "A vistas"])
tipo_pago = colp3.selectbox("Tipo de pago", ["Efectivo", "Tarjeta", "Transferencia"])
pago = Decimal(str(colp4.number_input("Pago recibido", min_value=0.0, step=1.0)))

subtotal1 = total
total_final = total * (Decimal(1) - descuento / Decimal(100))
cambio = pago - total_final if tipo_pago == "Efectivo" else Decimal("0.00")

st.metric("Subtotal", f"${subtotal1:.2f}")
st.metric("💰 Total a pagar", f"${total_final:.2f}")
st.metric("🔁 Cambio", f"${cambio:.2f}")


# --- GENERAR VENTA ---
# --- REGISTRAR VENTA Y GENERAR TICKET ---
if st.button("🧾 Registrar y Generar Ticket"):
    conexion = conectar_db()
    if not conexion:
        st.error("❌ No se pudo conectar a la base de datos.")
    else:
        cursor = None
        try:
            cursor = conexion.cursor()

            # --- Obtener ID del cliente ---
            id_cliente = None if cliente_otro else int(cliente_sel.split(" - ")[0])

            # --- Insertar venta ---
            sql_venta = """
                INSERT INTO VENTAS (ID_CLIENTE, TIPO_VENTA, MONTO_TOTAL, DESCUENTO, PAGO_TIPO, PAGO_RECIBIDO)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            datos_venta = (id_cliente, tipo_venta, float(total_final), float(descuento), tipo_pago, float(pago))
            cursor.execute(sql_venta, datos_venta)
            conexion.commit()
            id_venta = cursor.lastrowid

            # --- Insertar productos ---
            sql_prod = """
                INSERT INTO VENTA_PRODUCTOS
                (ID_VENTA, ID_PRODUCTO, DESCRIPCION, CLASIFICACION, CANTIDAD, PRECIO_UNITARIO, PRECIO_TOTAL)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            for p in lista_venta:
                prod_id = p["id_producto"] if p["id_producto"] != '0000' else None
                clasificacion = next((x[2] for x in productos if x[0] == p["id_producto"]), "M")
                datos_prod = (
                    id_venta,
                    prod_id,
                    p["desc"],
                    clasificacion,
                    int(p["cant"]),
                    float(p["precio"]),
                    float(p["subtotal"])
                )
                cursor.execute(sql_prod, datos_prod)
            conexion.commit()

            # --- Generar ticket ---
            cliente_nombre_final = cliente_otro if cliente_otro else cliente_sel
            pdf_path = generar_ticket(
                id_venta,
                cliente_nombre_final,
                lista_venta,
                total,
                descuento,
                total_final,
                pago,
                cambio,
                tipo_pago
            )

            st.success(f"✅ Venta registrada correctamente. Ticket generado: {pdf_path}")
            with open(pdf_path, "rb") as f:
                st.download_button("Descargar Ticket PDF", f,
                                   file_name=f"ticket_{id_venta}.pdf",
                                   mime="application/pdf")

        except Error as e:
            conexion.rollback()
            st.error(f"⚠️ Error al registrar la venta: {e}")

        finally:
            if cursor:
                cursor.close()
            conexion.close()












