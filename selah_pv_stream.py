import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from decimal import Decimal, InvalidOperation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import os
import time

# --- Configuración de Estilos y Colores ---
PRIMARY_COLOR = '#A2D5B0' # Verde suave
ACCENT_COLOR = '#F6A441' # Naranja vibrante
BG_LIGHT = '#FFFFFF'
TEXT_DARK = '#333333'
LOGO_PATH = "./www/logo.png"

# --- Estilos de Streamlit (Personalización con CSS) ---
st.markdown(f"""
    <style>
        .stButton>button {{
            background-color: {ACCENT_COLOR};
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 20px;
            font-weight: bold;
            transition: all 0.2s;
        }}
        .stButton>button:hover {{
            background-color: #F9C966;
            color: {TEXT_DARK};
        }}
        .stDownloadButton>button {{
            background-color: {PRIMARY_COLOR} !important;
            color: white !important;
            border-radius: 8px;
            border: none;
            padding: 10px 20px;
            font-weight: bold;
        }}
        .total-display {{
            font-size: 28px;
            color: {ACCENT_COLOR};
            font-weight: bold;
            margin-top: 10px;
        }}
        .cambio-display {{
            font-size: 20px;
            color: {TEXT_DARK};
            margin-bottom: 20px;
        }}
        .subheader {{
            font-size: 18px;
            font-weight: 600;
            color: {PRIMARY_COLOR};
            margin-top: 15px;
        }}
    </style>
""", unsafe_allow_html=True)


# --- 1. Inicialización de Estado y Datos Dummy ---

if 'product_rows' not in st.session_state:
    st.session_state.product_rows = [{'product_id': '', 'qty': 1, 'manual_price': 0.00, 'desc': '', 'clas': '', 'precio': Decimal('0.00')}]
if 'total' not in st.session_state:
    st.session_state.total = Decimal('0.00')
if 'cambio_msg' not in st.session_state:
    st.session_state.cambio_msg = "Cambio: $0.00"
if 'cambio_val' not in st.session_state:
    st.session_state.cambio_val = Decimal('0.00')
if 'total_final_val' not in st.session_state:
    st.session_state.total_final_val = Decimal('0.00')

# --- 2. Funciones de Conexión y Datos (Cacheables) ---

@st.cache_resource(ttl=3600)
def conectar_db():
    """Intenta conectar a la BD, si falla, retorna None."""
    try:
        # Nota: La conexión real requiere que la BD y las credenciales sean accesibles
        # desde el entorno donde se ejecuta Streamlit.
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='a?o14_8Fi5)#',
            database='SELAH_BASE'
        )
        return conexion
    except Error:
        # st.error(f"No se pudo conectar a la base de datos: {e}. Usando datos dummy.")
        return None

@st.cache_data(ttl=600)
def obtener_clientes():
    """Obtiene clientes o usa datos dummy."""
    conexion = conectar_db()
    if conexion is None:
        return [(1, "Juan Perez"), (2, "Maria Lopez"), (3, "Público General")]
    
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT ID_CLIENTE, NOMBRE_CLIENTE, APELLIDO FROM CLIENTES")
        result = cursor.fetchall()
        clientes_list = [(r[0], f"{r[1]} {r[2]}") for r in result]
        return clientes_list
    finally:
        cursor.close()
        conexion.close()

@st.cache_data(ttl=600)
def obtener_pulseras():
    """Obtiene productos o usa datos dummy."""
    conexion = conectar_db()
    
    productos_db = [('0000', 'Otro/Manual', 'M', Decimal('0.00'))]
    
    if conexion is None:
        productos_db.extend([
            ('PUL101', 'Pulsera Clasica', 'C', Decimal('15.50')),
            ('PUL202', 'Tobillera Premium', 'T', Decimal('22.00')),
            ('SERV01', 'Servicio de Grabado', 'S', Decimal('5.00'))
        ])
        return productos_db
    
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT ID_PRODUCTO, DESCRIPCION, CLASIFICACION, PRECIO_CLASIFICADO FROM PULSERAS")
        productos_db.extend(cursor.fetchall())
        return productos_db
    finally:
        cursor.close()
        conexion.close()

# --- Datos iniciales ---
pulseras = obtener_pulseras()
clientes_data = obtener_clientes()
clientes_map = {f"{c[0]} - {c[1]}": c[0] for c in clientes_data}
pulseras_map = {p[0]: {'desc': p[1], 'clas': p[2], 'precio': p[3]} for p in pulseras}
pulseras_options = [p[0] for p in pulseras]

# --- 3. Funciones de Cálculo y Lógica Principal ---

def calcular_cambio_streamlit():
    """Calcula el cambio y actualiza el estado de sesión."""
    tipo_venta = st.session_state.sale_type
    pago_tipo = st.session_state.payment_type
    total = st.session_state.total_final_val
    
    if tipo_venta == "A vistas":
        st.session_state.cambio_msg = "Préstamo (A Vistas)"
        st.session_state.cambio_val = Decimal('0.00')
        return

    try:
        if pago_tipo != "Efectivo":
            st.session_state.cambio_msg = "Cambio: $0.00"
            st.session_state.cambio_val = Decimal('0.00')
            return

        recibido = Decimal(st.session_state.payment_received or "0")
        cambio = recibido - total
        st.session_state.cambio_val = cambio

        if cambio < 0:
            st.session_state.cambio_msg = f"Faltan ${abs(cambio):.2f}"
        else:
            st.session_state.cambio_msg = f"Cambio: ${cambio:.2f}"
    except (InvalidOperation, TypeError):
        st.session_state.cambio_msg = "Cambio: $0.00"
        st.session_state.cambio_val = Decimal('0.00')

def calcular_total_streamlit():
    """Calcula el total y actualiza el estado de sesión."""
    total_sin_descuento = Decimal('0.00')
    
    for row in st.session_state.product_rows:
        try:
            cant = int(row['qty'] or 0)
            
            if row['product_id'] == '0000':
                precio_unitario = Decimal(str(row['manual_price'] or 0.00))
            else:
                precio_unitario = row['precio']
            
            total_sin_descuento += cant * precio_unitario
            
        except (ValueError, InvalidOperation):
            continue
            
    descuento_percent = Decimal(str(st.session_state.discount or 0.00).replace("%",""))
    if descuento_percent > 30:
        st.warning("El descuento máximo es 30%")
        descuento_percent = Decimal('30')
        
    total_final = total_sin_descuento * (Decimal('1') - descuento_percent / Decimal('100'))
    
    st.session_state.total = total_sin_descuento
    st.session_state.total_final_val = total_final
    st.session_state.descuento_percent = descuento_percent
    
    calcular_cambio_streamlit()

def generar_ticket_pdf(id_venta, cliente_nombre, productos, subtotal_sin_descuento, descuento_porcentaje, descuento_monto, total_final, pago_recibido, cambio, tipo_pago):
    """Genera el ticket PDF y retorna los bytes."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    x_start = 50 
    x_center = width / 2
    y = height - 50 # Posición de inicio superior
    
    # Intento de cargar Logo
    try:
        if os.path.exists("./www/logo.png"):
            logo_w, logo_h = 100, 100
            logo_x = x_center - (logo_w / 2)
            c.drawImage("./www/logo.png", logo_x, y - logo_h, width=logo_w, height=logo_h)
            y -= logo_h + 10
    except Exception:
        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x_center, y, "SELAH - TPV")
        y -= 10

    # Título y Detalles
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x_center, y, "SELAH - TICKET DE VENTA") 
    y -= 30
    c.setFont("Helvetica", 10)
    c.drawString(x_start, y, f"Venta ID: {id_venta}")
    y -= 15
    c.drawString(x_start, y, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.drawString(x_start, y, f"Cliente: {cliente_nombre}")
    y -= 25

    # Encabezados de Productos 
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_start, y, "Producto")
    c.drawString(250, y, "Código")
    c.drawString(380, y, "Cant.")
    c.drawString(430, y, "Precio")
    c.drawString(500, y, "Subtotal")
    y -= 10
    c.line(x_start, y, 550, y)
    y -= 15

    # Detalle de Productos
    c.setFont("Helvetica", 10)
    for p in productos:
        if y < 100: c.showPage(); y = height - 50
        
        c.drawString(x_start, y, p['desc'][:25])
        c.drawString(250, y, p['id_producto'])
        c.drawRightString(410, y, str(p['cant']))
        c.drawRightString(470, y, f"${p['precio']:.2f}")
        c.drawRightString(550, y, f"${p['subtotal']:.2f}")
        y -= 15
        
    y -= 10
    c.line(x_start, y, 550, y)
    y -= 20

    # Resumen de Totales
    c.setFont("Helvetica", 10)
    c.drawRightString(470, y, "SUBTOTAL:")
    c.drawRightString(550, y, f"${subtotal_sin_descuento:.2f}")
    y -= 15
    
    if descuento_porcentaje > 0:
        c.drawRightString(470, y, f"DESCUENTO ({descuento_porcentaje:.2f}%):")
        c.drawRightString(550, y, f"-${descuento_monto:.2f}")
        y -= 15
        
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(470, y, "TOTAL A PAGAR:")
    c.drawRightString(550, y, f"${total_final:.2f}")
    y -= 20
    
    c.setFont("Helvetica", 10)
    c.drawRightString(550, y, f"RECIBIDO: ${pago_recibido:.2f}")
    y -= 15
    
    c.setFont("Helvetica-Bold", 12)
    if cambio >= 0:
        c.drawRightString(550, y, f"CAMBIO: ${cambio:.2f}")
    else:
        c.drawRightString(550, y, f"FALTA: ${abs(cambio):.2f}")
            
    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(x_start, y, f"Tipo de pago: {tipo_pago}")
    y -= 40
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width/2, y, "Gracias por su compra. ¡Vuelva pronto!") 

    c.save()
    return buffer.getvalue()

def registrar_venta_streamlit():
    """Recolecta datos, simula registro y genera ticket."""
    total_final = st.session_state.total_final_val
    subtotal_sin_descuento = st.session_state.total
    descuento_porcentaje = st.session_state.descuento_percent

    if subtotal_sin_descuento == 0:
        st.error("No hay productos para registrar.")
        return

    # Validaciones de Pago
    tipo_venta = st.session_state.sale_type
    pago_tipo = st.session_state.payment_type
    pago_recibido = Decimal(st.session_state.payment_received or '0')

    if tipo_venta == "A vistas":
        pago_recibido = Decimal('0.00')
        cambio = Decimal('0.00')
        pago_tipo = "N/A"
    else:
        if pago_tipo == "Efectivo" and pago_recibido < total_final:
            st.warning("El monto recibido es menor al total.")
            return
        cambio = st.session_state.cambio_val

    descuento_monto = subtotal_sin_descuento * (descuento_porcentaje / Decimal('100'))

    # Obtener cliente
    cliente_seleccionado = st.session_state.client_combo
    cliente_id = clientes_map.get(cliente_seleccionado)
    cliente_nombre = st.session_state.client_other or cliente_seleccionado.split(" - ")[1]

    # Simular ID de venta (o conseguir el real si hay conexión)
    id_venta = int(time.time() * 1000) # Usamos un timestamp como ID simulado
    
    productos_ticket = []
    conexion = conectar_db()
    
    if conexion is not None:
        # Lógica de inserción real en MySQL
        try:
            cursor = conexion.cursor()
            
            # 1. Insertar VENTA
            sql_venta = """
            INSERT INTO VENTAS (FECHA_HORA, ID_CLIENTE, NOMBRE_CLIENTE, TIPO_VENTA, MONTO_TOTAL, DESCUENTO, PAGO_TIPO, PAGO_RECIBIDO)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """
            cursor.execute(sql_venta, (
                datetime.now(), cliente_id, cliente_nombre, tipo_venta, float(total_final), float(descuento_porcentaje), pago_tipo, float(pago_recibido)
            ))
            id_venta = cursor.lastrowid # Obtener el ID real
            
            # 2. Insertar VENTA_PRODUCTOS
            for row in st.session_state.product_rows:
                producto_id = row['product_id']
                cantidad = int(row['qty'] or 0)
                if cantidad == 0 or not producto_id: continue

                precio_unitario_float = float(Decimal(row['manual_price'])) if producto_id == '0000' else float(row['precio'])
                descripcion_producto = row['desc']
                clasificacion_producto = row['clas']
                subtotal = precio_unitario_float * cantidad

                cursor.execute("""
                    INSERT INTO VENTA_PRODUCTOS (ID_VENTA, ID_PRODUCTO, DESCRIPCION, CLASIFICACION, CANTIDAD, PRECIO_UNITARIO, PRECIO_TOTAL)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (id_venta, producto_id, descripcion_producto, clasificacion_producto, cantidad, precio_unitario_float, subtotal))
                
                productos_ticket.append({'id_producto': producto_id, 'desc': descripcion_producto, 'cant': cantidad, 'precio': precio_unitario_float, 'subtotal': subtotal})

            conexion.commit()
            st.success(f"Venta registrada exitosamente en la BD (ID: {id_venta})")
        except Error as e:
            st.error(f"Error al registrar la venta en la BD: {e}. Se generará el ticket de forma local.")
            # Si falla la BD, rellenamos productos_ticket de forma local
            for row in st.session_state.product_rows:
                producto_id = row['product_id']
                cantidad = int(row['qty'] or 0)
                if cantidad == 0 or not producto_id: continue
                precio_unitario_float = float(Decimal(row['manual_price'])) if producto_id == '0000' else float(row['precio'])
                subtotal = precio_unitario_float * cantidad
                productos_ticket.append({'id_producto': producto_id, 'desc': row['desc'], 'cant': cantidad, 'precio': precio_unitario_float, 'subtotal': subtotal})

        finally:
            if conexion:
                cursor.close()
                conexion.close()
    else:
        # Si no hay conexión (Datos Dummy)
        st.warning("Sin conexión a la BD. Simulación de registro local.")
        for row in st.session_state.product_rows:
            producto_id = row['product_id']
            cantidad = int(row['qty'] or 0)
            if cantidad == 0 or not producto_id: continue
            precio_unitario_float = float(Decimal(row['manual_price'])) if producto_id == '0000' else float(row['precio'])
            subtotal = precio_unitario_float * cantidad
            productos_ticket.append({'id_producto': producto_id, 'desc': row['desc'], 'cant': cantidad, 'precio': precio_unitario_float, 'subtotal': subtotal})
        st.success(f"Venta simulada (ID: {id_venta})")


    # Generar Ticket y permitir descarga
    pdf_bytes = generar_ticket_pdf(
        id_venta, cliente_nombre, productos_ticket, float(subtotal_sin_descuento), float(descuento_porcentaje), 
        float(descuento_monto), float(total_final), float(pago_recibido), float(cambio), pago_tipo
    )
    
    st.download_button(
        label="Descargar Ticket PDF",
        data=pdf_bytes,
        file_name=f"ticket_venta_{id_venta}.pdf",
        mime="application/pdf"
    )

    # Limpiar campos después del registro
    limpiar_campos_streamlit()


def limpiar_campos_streamlit():
    """Limpia el estado de sesión y fuerza un re-render."""
    st.session_state.product_rows = [{'product_id': '', 'qty': 1, 'manual_price': 0.00, 'desc': '', 'clas': '', 'precio': Decimal('0.00')}]
    st.session_state.total = Decimal('0.00')
    st.session_state.total_final_val = Decimal('0.00')
    st.session_state.cambio_msg = "Cambio: $0.00"
    st.session_state.cambio_val = Decimal('0.00')
    st.session_state.descuento = 0.00
    st.session_state.client_combo = clientes_data[0][1] # Poner cliente por defecto
    st.session_state.client_other = ""
    st.session_state.sale_type = "Contado"
    st.session_state.payment_type = "Efectivo"
    st.session_state.payment_received = 0.00
    # Forzar el re-ejecución de la app para limpiar widgets
    st.rerun()

# --- 4. Funciones de Gestión de Productos ---

def agregar_fila():
    st.session_state.product_rows.append({'product_id': '', 'qty': 1, 'manual_price': 0.00, 'desc': '', 'clas': '', 'precio': Decimal('0.00')})
    calcular_total_streamlit()

def eliminar_fila():
    if len(st.session_state.product_rows) > 1:
        st.session_state.product_rows.pop()
    else:
        # Solo limpiar la única fila restante
        st.session_state.product_rows = [{'product_id': '', 'qty': 1, 'manual_price': 0.00, 'desc': '', 'clas': '', 'precio': Decimal('0.00')}]
    calcular_total_streamlit()
    

def actualizar_fila(index, field, value):
    """Actualiza un campo específico de una fila de producto."""
    if field == 'product_id':
        info = pulseras_map.get(value, pulseras_map['0000'])
        st.session_state.product_rows[index]['product_id'] = value
        st.session_state.product_rows[index]['desc'] = info['desc']
        st.session_state.product_rows[index]['clas'] = info['clas']
        st.session_state.product_rows[index]['precio'] = info['precio']
    
    elif field == 'manual_price':
        try:
            st.session_state.product_rows[index][field] = float(value or 0.00)
        except ValueError:
            st.session_state.product_rows[index][field] = 0.00
    
    elif field == 'qty':
        try:
            st.session_state.product_rows[index][field] = int(value or 0)
        except ValueError:
            st.session_state.product_rows[index][field] = 0

    calcular_total_streamlit()


# --- 5. Interfaz de Usuario (Streamlit) ---

st.title("🛍️ TPV Dinámico SELAH (Mobile-Friendly)")

# Layout de 2 columnas principales (se apilarán en móvil)
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown('<p class="subheader">Información del Cliente</p>', unsafe_allow_html=True)
    
    # Cliente Registrado (simulación de autocompletado con selectbox)
    clientes_list = [f"{c[0]} - {c[1]}" for c in clientes_data]
    st.selectbox(
        "Cliente Registrado:",
        clientes_list,
        index=clientes_list.index(next((c for c in clientes_list if "Público General" in c), clientes_list[0])),
        key='client_combo',
        help="Seleccione un cliente registrado por su ID o nombre."
    )
    
    st.text_input("Cliente (Otro) [Si no está registrado]:", key='client_other', placeholder="Nombre/Empresa")
    
    st.divider()

    st.markdown('<p class="subheader">Detalles de Pago y Venta</p>', unsafe_allow_html=True)
    
    # Campos de Venta
    st.number_input("Descuento (%):", min_value=0.0, max_value=30.0, key='discount', 
                    on_change=calcular_total_streamlit, format="%.2f", step=1.0)
    
    st.selectbox("Tipo de venta:", ["Contado", "A cuenta", "A vistas"], key='sale_type', on_change=calcular_cambio_streamlit)

    # Lógica de deshabilitar campos para "A vistas"
    is_a_vistas = st.session_state.sale_type == "A vistas"
    
    st.selectbox("Tipo de pago:", ["Efectivo", "Tarjeta", "Deposito", "N/A"], key='payment_type', 
                 on_change=calcular_cambio_streamlit, disabled=is_a_vistas)
    
    st.number_input("Pago recibido:", min_value=0.00, key='payment_received', format="%.2f", 
                    on_change=calcular_cambio_streamlit, disabled=is_a_vistas)

    st.divider()
    
    # Resumen de Totales
    st.markdown(f'<div class="total-display">TOTAL: ${st.session_state.total_final_val:.2f}</div>', unsafe_allow_html=True)
    
    color_cambio = '#F8B8B2' if 'Faltan' in st.session_state.cambio_msg else TEXT_DARK
    st.markdown(f'<div class="cambio-display" style="color: {color_cambio};">{st.session_state.cambio_msg}</div>', unsafe_allow_html=True)


    # Botón de Acción Principal
    st.button("✅ Registrar Venta", on_click=registrar_venta_streamlit)
    st.button("Limpiar Campos", on_click=limpiar_campos_streamlit)


with col2:
    st.markdown('<p class="subheader">Productos de la Venta</p>', unsafe_allow_html=True)

    # Contenedor para las filas dinámicas
    product_container = st.container()
    
    with product_container:
        # Encabezados de tabla
        cols = st.columns([2, 1, 1, 0.2])
        cols[0].markdown("**ID Producto**")
        cols[1].markdown("**Cantidad**")
        cols[2].markdown("**Precio/Manual**")
        
        # Iteración de las filas de producto
        for i, row in enumerate(st.session_state.product_rows):
            key_suffix = f"_{i}"
            
            product_cols = st.columns([2, 1, 1, 0.2])
            
            # 1. Selector de Producto (Combo)
            selected_product = product_cols[0].selectbox(
                "ID Producto",
                pulseras_options,
                index=pulseras_options.index(row['product_id']) if row['product_id'] in pulseras_options else 0,
                key=f"product_id{key_suffix}",
                label_visibility="collapsed",
                on_change=actualizar_fila, args=(i, 'product_id', st.session_state[f"product_id{key_suffix}"])
            )
            
            # 2. Cantidad (Entry)
            product_cols[1].number_input(
                "Cantidad",
                min_value=0,
                key=f"qty{key_suffix}",
                value=row['qty'],
                label_visibility="collapsed",
                on_change=actualizar_fila, args=(i, 'qty', st.session_state[f"qty{key_suffix}"])
            )
            
            # 3. Precio/Manual (Entry - se muestra solo si es '0000')
            if selected_product == '0000':
                product_cols[2].number_input(
                    "Precio Manual",
                    min_value=0.00,
                    key=f"manual_price{key_suffix}",
                    value=row['manual_price'],
                    format="%.2f",
                    label_visibility="collapsed",
                    on_change=actualizar_fila, args=(i, 'manual_price', st.session_state[f"manual_price{key_suffix}"])
                )
            else:
                # Mostrar el precio de la BD como texto simple (no editable)
                product_cols[2].markdown(f"**${row['precio']:.2f}**")
                
            # 4. Botón de Descripción (simulado)
            product_cols[3].markdown(f"<span style='color: {TEXT_DARK}; font-size: 10px;'>{row['desc'][:1]}...</span>", unsafe_allow_html=True)
            
            st.session_state.product_rows[i]['product_id'] = selected_product
            # Forzar actualización de precio y descripción en el estado de la fila al cargar
            if row['product_id'] != selected_product:
                 actualizar_fila(i, 'product_id', selected_product)


    # Botones de gestión de productos
    st.divider()
    btn_col1, btn_col2 = st.columns(2)
    btn_col1.button("➕ Agregar Producto", on_click=agregar_fila)
    btn_col2.button("➖ Eliminar Producto", on_click=eliminar_fila)

# --- Inicialización del cálculo (para asegurar que el total sea correcto al inicio) ---
calcular_total_streamlit()
