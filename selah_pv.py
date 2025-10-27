# -*- coding: utf-8 -*-
"""
TPV Dinámico con interfaz modernizada (minimalista y funcional).
Autor: Arie Brito
Actualizado: 23 octubre 2025

Nota: Se ha refactorizado la interfaz de Tkinter para usar un estilo moderno
y se ha añadido el logo al ticket PDF.
"""
import mysql.connector
from mysql.connector import Error
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal, InvalidOperation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# --- Configuración de Estilos y Colores ---
PRIMARY_COLOR = '#A2D5B0'
ACCENT_COLOR = '#F6A441'
BG_LIGHT = '#FFFFFF'
TEXT_DARK = '#333333'
BUTTON_HOVER = '#F9C966' 
LOGO_PATH = r"\www\logo.png"

# Variable global para almacenar la lista de clientes
clientes = []

# --- Conexión a MySQL (sin cambios en la lógica) ---
def conectar_db():
    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='a?o14_8Fi5)#',
            database='SELAH_BASE'
        )
        return conexion
    except Error as e:
        messagebox.showerror("Error", f"No se pudo conectar a la base de datos: {e}")
        return None

# --- Obtener clientes (MODIFICADA para actualizar la global) ---
def obtener_clientes():
    """Obtiene clientes de la BD y actualiza la lista global 'clientes'."""
    global clientes
    conexion = conectar_db()
    if conexion is None:
        clientes = []
        return []
        
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT ID_CLIENTE, NOMBRE_CLIENTE, APELLIDO FROM CLIENTES")
        result = cursor.fetchall()
        
        # Actualiza la variable global clientes
        clientes = [(r[0], f"{r[1]} {r[2]}") for r in result]
        return clientes
    finally:
        cursor.close()
        conexion.close()

# --- Obtener productos (Clasificación 'M' para manual) ---
def obtener_pulseras():
    conexion = conectar_db()
    if conexion is None:
        # ID '0000' para productos manuales, CLASIFICACION: 'M' (Manual)
        return [('0000', 'Otro/Manual', 'M', Decimal('0.00'))] 
        
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT ID_PRODUCTO, DESCRIPCION, CLASIFICACION, PRECIO_CLASIFICADO FROM PULSERAS")
        productos_db = cursor.fetchall()
        # Añadimos el ID 0000 con clasificación 'M' para BD
        productos_db.append(('0000', 'Otro/Manual', 'M', Decimal('0.00')))
        return productos_db
    finally:
        cursor.close()
        conexion.close()
        
# --- Función para el autocompletado del cliente ---
def autocompletar_cliente(event):
    texto_escrito = combo_cliente.get()
    clientes_formateados = [f"{c[0]} - {c[1]}" for c in clientes]
    
    if not texto_escrito:
        nuevos_valores = clientes_formateados
    else:
        texto_escrito_lower = texto_escrito.lower()
        nuevos_valores = [valor for valor in clientes_formateados if texto_escrito_lower in valor.lower()]

    combo_cliente['values'] = nuevos_valores
    
    try:
        combo_cliente.set(texto_escrito)
        if nuevos_valores:
            combo_cliente.focus_set() 
            combo_cliente.tk.call(combo_cliente, 'post') 
    except tk.TclError:
        pass
    

# --- Crear ventana principal y estilos ---
root = tk.Tk()
root.title("TPV Dinámico SELAH - Venta de Pulseras")
root.configure(bg=BG_LIGHT)

style = ttk.Style()
style.theme_use('clam') 

# Estilo general
style.configure('TFrame', background=BG_LIGHT)
style.configure('TLabel', background=BG_LIGHT, foreground=TEXT_DARK, font=('Inter', 10))
style.configure('TButton', background=ACCENT_COLOR, foreground=BG_LIGHT, font=('Inter', 10, 'bold'), borderwidth=0, relief='flat')
style.map('TButton',
          background=[('active', BUTTON_HOVER), ('pressed', ACCENT_COLOR)],
          foreground=[('active', TEXT_DARK)])

# Estilos específicos
style.configure('Accent.TButton', background=PRIMARY_COLOR, foreground=BG_LIGHT)
style.map('Accent.TButton',
          background=[('active', PRIMARY_COLOR), ('pressed', PRIMARY_COLOR)],
          foreground=[('active', BG_LIGHT)])

style.configure('TCombobox', font=('Inter', 10), fieldbackground=BG_LIGHT)
style.configure('TEntry', font=('Inter', 10), fieldbackground=BG_LIGHT)


# --- Frame Principal (Layout de 2 Columnas) ---
main_frame = ttk.Frame(root, padding="20 20 20 20")
main_frame.pack(fill="both", expand=True)

left_frame = ttk.Frame(main_frame, padding="0 0 20 0")
left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

right_frame = ttk.Frame(main_frame, padding="0 0 0 0")
right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

main_frame.grid_columnconfigure(1, weight=1)


# --- 1. Frame de Clientes (LEFT) ---
client_frame = ttk.LabelFrame(left_frame, text="Información del Cliente", padding="15 15 15 15")
client_frame.pack(fill="x", pady=10)

ttk.Label(client_frame, text="Cliente Registrado:", style='TLabel').grid(row=0, column=0, sticky="w", pady=5)
obtener_clientes() 

combo_cliente = ttk.Combobox(client_frame, values=[f"{c[0]} - {c[1]}" for c in clientes], width=30, style='TCombobox')
combo_cliente.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

combo_cliente.bind('<KeyRelease>', autocompletar_cliente)

ttk.Button(client_frame, text="Nuevo cliente", command=lambda: abrir_registro_cliente(combo_cliente, obtener_clientes), style='TButton').grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

ttk.Label(client_frame, text="Cliente (Otro):", style='TLabel').grid(row=2, column=0, sticky="w", pady=5)
entry_cliente_otro = ttk.Entry(client_frame, style='TEntry')
entry_cliente_otro.grid(row=2, column=1, sticky="ew", padx=10, pady=5)


# --- 2. Frame de Productos (RIGHT) ---
products_frame = ttk.LabelFrame(right_frame, text="Productos de la Venta", padding="15 15 15 15")
products_frame.pack(fill="both", expand=True, pady=10)

pulseras = obtener_pulseras()
filas_productos = []

frame_productos = ttk.Frame(products_frame, padding="5 5 5 5")
frame_productos.pack(fill="both", expand=True)

# Encabezados de tabla
ttk.Label(frame_productos, text="ID Producto", font=('Inter', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5)
ttk.Label(frame_productos, text="Cantidad", font=('Inter', 10, 'bold')).grid(row=0, column=1, padx=5, pady=5)
ttk.Label(frame_productos, text="Precio/Manual", font=('Inter', 10, 'bold')).grid(row=0, column=2, padx=5, pady=5) 

def agregar_fila():
    fila_index = len(filas_productos) + 1 
    fila = {}
    
    def actualizar_precio(event):
        selected = fila["combo"].get()
        
        # --- LÓGICA CLAVE DE PRECIO Y CLASIFICACIÓN MANUAL ---
        if selected == '0000':
            fila["precio_entry"].grid(row=fila_index, column=2, padx=5, pady=3, sticky="ew")
            fila["desc"] = "Producto/Servicio Manual" 
            fila["clas"] = "M" 
            fila["precio"] = Decimal('0.00') 
        else:
            fila["precio_entry"].grid_forget()
            for p in pulseras:
                if p[0] == selected:
                    try:
                        fila["precio"] = Decimal(str(p[3]))
                    except InvalidOperation:
                        fila["precio"] = Decimal('0.00')
                    fila["desc"] = p[1]
                    fila["clas"] = p[2]
                    break
        calcular_total() 
        
    def leer_precio_manual(event):
        calcular_total()
        
    fila["combo"] = ttk.Combobox(frame_productos, values=[p[0] for p in pulseras], width=20)
    fila["combo"].grid(row=fila_index, column=0, padx=5, pady=3, sticky="ew")
    fila["combo"].bind("<<ComboboxSelected>>", actualizar_precio)
    
    fila["cant"] = ttk.Entry(frame_productos, width=5)
    fila["cant"].grid(row=fila_index, column=1, padx=5, pady=3, sticky="ew")
    fila["cant"].bind("<KeyRelease>", lambda e: calcular_total()) 
    
    fila["precio_entry"] = ttk.Entry(frame_productos, width=10, justify='right')
    fila["precio_entry"].bind("<KeyRelease>", leer_precio_manual)
    
    fila["precio"] = Decimal('0.00')
    fila["desc"] = ""
    fila["clas"] = ""
    filas_productos.append(fila)

def eliminar_fila():
    if filas_productos:
        fila = filas_productos.pop()
        fila["combo"].grid_forget()
        fila["cant"].grid_forget()
        if "precio_entry" in fila:
            fila["precio_entry"].grid_forget()
            
        calcular_total() 
        
# Botones de gestión de productos
product_buttons_frame = ttk.Frame(products_frame)
product_buttons_frame.pack(fill="x", pady=10)
ttk.Button(product_buttons_frame, text="+ Producto", command=agregar_fila, style='TButton').pack(side="left", padx=5)
ttk.Button(product_buttons_frame, text="- Producto", command=eliminar_fila, style='Accent.TButton').pack(side="left", padx=5)


# --- 3. Frame de Pago y Resumen (LEFT) ---
payment_frame = ttk.LabelFrame(left_frame, text="Detalles de Pago y Venta", padding="15 15 15 15")
payment_frame.pack(fill="x", pady=10)

# Campos de Venta
ttk.Label(payment_frame, text="Descuento (%):", style='TLabel').grid(row=0, column=0, sticky="w", pady=5)
entry_descuento = ttk.Entry(payment_frame, width=15)
entry_descuento.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

ttk.Label(payment_frame, text="Tipo de venta:", style='TLabel').grid(row=1, column=0, sticky="w", pady=5)
combo_tipo_venta = ttk.Combobox(payment_frame, values=["Contado","A cuenta","A vistas"], width=15)
combo_tipo_venta.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
combo_tipo_venta.set("Contado")

ttk.Label(payment_frame, text="Tipo de pago:", style='TLabel').grid(row=2, column=0, sticky="w", pady=5)
combo_pago = ttk.Combobox(payment_frame, values=["Efectivo","Tarjeta","Deposito"], width=15)
combo_pago.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
combo_pago.set("Efectivo")

ttk.Label(payment_frame, text="Pago recibido:", style='TLabel').grid(row=3, column=0, sticky="w", pady=5)
entry_pago = ttk.Entry(payment_frame, width=15)
entry_pago.grid(row=3, column=1, sticky="ew", padx=10, pady=5)

# Separador
ttk.Separator(payment_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)

# Resumen de Totales
label_total = ttk.Label(payment_frame, text="TOTAL: $0.00", font=('Inter', 14, 'bold'), foreground=ACCENT_COLOR)
label_total.grid(row=5, column=0, columnspan=2, pady=(5, 5), sticky="w")
label_cambio = ttk.Label(payment_frame, text="Cambio: $0.00", font=('Inter', 12))
label_cambio.grid(row=6, column=0, columnspan=2, pady=(0, 5), sticky="w")


# --- Funciones de cálculo y gestión de venta ---

def calcular_cambio(event=None):
    if combo_tipo_venta.get() == "A vistas":
        label_cambio.config(text="Préstamo", foreground=TEXT_DARK)
        return
        
    try:
        if combo_pago.get() != "Efectivo":
            label_cambio.config(text="Cambio: $0.00", foreground=TEXT_DARK)
            return
            
        total_str = label_total.cget("text").replace("TOTAL: $", "")
        total = Decimal(total_str)
        recibido = Decimal(entry_pago.get() or "0")
        cambio = recibido - total
        if cambio < 0:
            label_cambio.config(text=f"Faltan ${abs(cambio):.2f}", foreground='#F8B8B2')
        else:
            label_cambio.config(text=f"Cambio: ${cambio:.2f}", foreground=TEXT_DARK)
    except Exception:
        label_cambio.config(text="Cambio: $0.00", foreground=TEXT_DARK)


def calcular_total():
    total_sin_descuento = Decimal('0.00')
    for fila in filas_productos:
        try:
            cant = int(fila["cant"].get() or 0)
            
            # --- LÓGICA DE LECTURA DE PRECIO ---
            if fila["combo"].get() == '0000':
                # Leer el precio del Entry de precio manual
                precio_str = fila["precio_entry"].get() or "0"
                precio_unitario = Decimal(precio_str)
            else:
                # Usar el precio almacenado de la BD
                if not isinstance(fila["precio"], Decimal):
                     fila["precio"] = Decimal(str(fila["precio"]))
                precio_unitario = fila["precio"]
                
            total_sin_descuento += cant * precio_unitario 
            
        except ValueError:
            continue
        except InvalidOperation:
            continue
        except Exception:
            continue

    descuento_str = entry_descuento.get() or "0"
    descuento_str = descuento_str.replace("%","")
    try:
        descuento = Decimal(descuento_str)
    except InvalidOperation:
        descuento = Decimal('0') 
        
    if descuento > 30:
        messagebox.showwarning("Alerta","El descuento máximo es 30%")
        descuento = Decimal('30')
        entry_descuento.delete(0, tk.END)
        entry_descuento.insert(0,"30")

    total_final = total_sin_descuento * (Decimal('1') - descuento/Decimal('100'))
    label_total.config(text=f"TOTAL: ${total_final:.2f}")
    
    calcular_cambio()
    
    return total_final, total_sin_descuento, descuento
    
def gestionar_tipo_venta(event=None):
    tipo_venta = combo_tipo_venta.get()
    
    if tipo_venta == "A vistas":
        combo_pago.config(state='disabled')
        entry_pago.config(state='disabled')
        
        combo_pago.set("N/A")
        entry_pago.delete(0, tk.END)
        label_cambio.config(text="Préstamo", foreground=TEXT_DARK)
        
    else:
        combo_pago.config(state='normal')
        entry_pago.config(state='normal')
        
        if combo_pago.get() == "N/A":
            combo_pago.set("Efectivo")
            
        calcular_cambio()

# --- Funciones de registro de cliente ---

def abrir_registro_cliente(combo_widget, obtener_clientes_func):
    ventana_cliente = tk.Toplevel(root)
    ventana_cliente.title("Registrar nuevo cliente")
    ventana_cliente.configure(bg=BG_LIGHT)
    
    style.configure('Toplevel.TLabel', background=BG_LIGHT)
    style.configure('Toplevel.TCheckbutton', background=BG_LIGHT)
    
    campos = ["Nombre", "Apellido", "Edad", "Correo", "Teléfono", "Dirección"]
    entries = {}
    
    frame_reg = ttk.Frame(ventana_cliente, padding="15", style='TFrame')
    frame_reg.pack(padx=10, pady=10)
    
    for i, campo in enumerate(campos):
        ttk.Label(frame_reg, text=f"{campo}:", style='Toplevel.TLabel').grid(row=i, column=0, sticky="w", pady=2)
        entry = ttk.Entry(frame_reg, style='TEntry')
        entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
        entries[campo.lower()] = entry

    var_preferente = tk.BooleanVar()
    ttk.Checkbutton(frame_reg, text="Cliente preferente", variable=var_preferente, style='Toplevel.TCheckbutton').grid(row=6, column=0, columnspan=2, sticky="w", pady=5)

    var_promos = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame_reg, text="Recibe promociones", variable=var_promos, style='Toplevel.TCheckbutton').grid(row=7, column=0, columnspan=2, sticky="w", pady=5)

    def guardar_cliente():
        conexion = conectar_db()
        if conexion is None:
            return
        cursor = conexion.cursor()
        try:
            sql = """
            INSERT INTO CLIENTES (NOMBRE_CLIENTE, APELLIDO, EDAD, CORREO, TELEFONO, DIRECCION, PREFERENTE, PROMOS)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """
            datos = (
                entries['nombre'].get(),
                entries['apellido'].get(),
                int(entries['edad'].get()) if entries['edad'].get().isdigit() else None,
                entries['correo'].get(),
                entries['teléfono'].get(),
                entries['dirección'].get(),
                var_preferente.get(),
                var_promos.get()
            )
            cursor.execute(sql, datos)
            conexion.commit()
            messagebox.showinfo("Éxito", "Cliente registrado correctamente")
            
            # --- LÓGICA DE REFRESCADO TRAS GUARDAR ---
            nuevos_clientes = obtener_clientes_func()
            
            combo_widget["values"] = [f"{c[0]} - {c[1]}" for c in nuevos_clientes]
            
            if nuevos_clientes:
                combo_widget.set(f"{nuevos_clientes[-1][0]} - {nuevos_clientes[-1][1]}")
            # ------------------------------------------
            
            ventana_cliente.destroy()
            
        except Error as e:
            messagebox.showerror("Error", f"No se pudo registrar el cliente: {e}")
        finally:
            cursor.close()
            conexion.close()

    ttk.Button(frame_reg, text="Guardar Cliente", command=guardar_cliente, style='Accent.TButton').grid(row=8, column=0, columnspan=2, pady=10, sticky="ew")

# --- Generar ticket PDF (MODIFICADA para centrado vertical) ---
def generar_ticket(id_venta, cliente_nombre, productos, subtotal_sin_descuento, descuento_porcentaje, descuento_monto, total_final, pago_recibido, cambio, tipo_pago):
    """Genera el ticket PDF, con el cuerpo centrado verticalmente."""
    carpeta_tickets = "tickets"
    os.makedirs(carpeta_tickets, exist_ok=True)
    archivo_pdf = os.path.join(carpeta_tickets, f"ticket_{id_venta}.pdf")

    c = canvas.Canvas(archivo_pdf, pagesize=letter)
    width, height = letter
    
    # --- Variables de Posición y Centrado Horizontal ---
    x_center = width / 2
    
    # El ancho del bloque de texto/tabla es de 500 puntos (de 50 a 550).
    # Coordenada X para el inicio de los detalles: 50
    x_start = 50 
    
    # --- Configuración del Logo (Centrado Horizontal) ---
    logo_w, logo_h = 100, 100 # Se mantiene el logo de 100x100
    logo_x = x_center - (logo_w / 2)
    
    # --- CÁLCULO PARA EL CENTRADO VERTICAL (CENTRAR EL BLOQUE DE CONTENIDO) ---
    
    # 1. Estimar la altura que ocupará el contenido total del ticket
    # Altura base (logo, título, detalles, totales y despedida): ~180 pts
    altura_base = 180 
    # Altura por cada línea de producto: 15 pts
    altura_productos = len(productos) * 15
    
    # 2. Altura vertical total del bloque de contenido
    altura_total_contenido = logo_h + altura_base + altura_productos + 30 # +30 por márgenes/espacios extra
    
    # 3. Determinar la coordenada Y de inicio (Margen superior + logo + espacio)
    # y = (altura_total_del_papel / 2) + (altura_total_del_contenido / 2)
    # Para que el contenido esté *centrado* en la página, la posición inicial 'y' 
    # debe ser: La mitad de la página, más la mitad del contenido, menos un margen superior.
    # Una forma más simple: Empezar en la mitad superior de la página y restar la mitad del contenido
    
    # Coordenada Y donde *termina* el bloque de contenido (ejemplo: 50 pts desde abajo)
    y_final = 50 
    
    # Coordenada Y donde *empezamos* a dibujar (parte superior del logo)
    y_inicio = height - y_final # Si empieza arriba
    
    # Calcula el punto de inicio 'y' para centrar todo el bloque
    y = (height + altura_total_contenido) / 1.25 # Posición media
    y = min(y, height - 50) # Asegura que no se salga del margen superior (ej: 50 pts)
    
    # Y de inicio: La coordenada 'y' más alta que dibujaremos, que es el borde superior del logo
    logo_y = y - logo_h 
    
    # --------------------------------------------------------------------------
    
    # --- LOGO DE LA EMPRESA (Centrado Horizontal) ---
    try:
        ruta_logo = LOGO_PATH
        if os.path.exists("./www/logo.png"):
             ruta_logo = "./www/logo.png"
        elif not os.path.exists(ruta_logo):
             pass 
             
        if os.path.exists(ruta_logo):
             c.drawImage(ruta_logo, logo_x, logo_y, width=logo_w, height=logo_h)
        else:
             c.setFont("Helvetica-Bold", 8)
             c.drawString(logo_x, logo_y + 20, "SELAH")
             c.drawString(logo_x, logo_y + 10, "Logo Missing")

    except Exception as e:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x_start, y, f"Error cargando logo: {e}")
    
    # Ajustamos 'y' para que el primer texto (Título) vaya después del logo
    y = logo_y - 20 

    # Título del Ticket (Centrado en X, inicia debajo del logo)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(x_center, y, "SELAH - TICKET DE VENTA") 
    c.setFont("Helvetica", 10)
    y -= 30

    # Detalles de la Venta 
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
        c.drawString(x_start, y, p['desc'][:25])
        c.drawString(250, y, p['id_producto'])
        c.drawRightString(410, y, str(p['cant']))
        c.drawRightString(470, y, f"${p['precio']:.2f}")
        c.drawRightString(550, y, f"${p['subtotal']:.2f}")
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 80 

    y -= 10
    c.line(x_start, y, 550, y)
    y -= 20

    # Resumen de Totales
    
    # 1. Subtotal (antes del descuento)
    c.setFont("Helvetica", 10)
    c.drawRightString(470, y, "SUBTOTAL:")
    c.drawRightString(550, y, f"${subtotal_sin_descuento:.2f}")
    y -= 15
    
    # 2. Descuento aplicado (si es mayor a cero)
    if descuento_porcentaje > 0:
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.8, 0.2, 0.2) 
        c.drawRightString(470, y, f"DESCUENTO ({descuento_porcentaje:.2f}%):")
        c.drawRightString(550, y, f"-${descuento_monto:.2f}")
        c.setFillColorRGB(0, 0, 0) 
        y -= 15
        
    # 3. Total Final (después del descuento)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(470, y, "TOTAL A PAGAR:")
    c.drawRightString(550, y, f"${total_final:.2f}")
    y -= 20
    
    # 4. Pago y cambio
    c.setFont("Helvetica", 10)
    c.drawRightString(550, y, f"RECIBIDO: ${pago_recibido:.2f}")
    y -= 15
    
    # Cambio/Faltante
    c.setFont("Helvetica-Bold", 12)
    if cambio >= 0:
          c.drawRightString(550, y, f"CAMBIO: ${cambio:.2f}")
    else:
          c.setFillColorRGB(0.8, 0.2, 0.2) 
          c.drawRightString(550, y, f"FALTA: ${abs(cambio):.2f}")
          c.setFillColorRGB(0, 0, 0) 
          
    y -= 25
    c.setFont("Helvetica", 10)
    c.drawString(x_start, y, f"Tipo de pago: {tipo_pago}")
    y -= 40
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width/2, y, "Gracias por su compra. ¡Vuelva pronto!") 

    c.save()
    messagebox.showinfo("Ticket generado", f"Ticket guardado en:\n{archivo_pdf}")


# --- Registrar venta (MODIFICADA para incluir ID_PRODUCTO en productos_ticket) ---
def registrar_venta():
    resultado_calculo = calcular_total()
    if resultado_calculo is None:
        return
        
    total_final, subtotal_sin_descuento, descuento_porcentaje = resultado_calculo

    if subtotal_sin_descuento == 0:
        messagebox.showerror("Error","No hay productos para registrar")
        return

    tipo_venta = combo_tipo_venta.get()
    pago_tipo = combo_pago.get()

    try:
        pago_recibido = Decimal(entry_pago.get() or '0')
    except:
        pago_recibido = Decimal('0.00')
        
    if tipo_venta == "A vistas":
        pago_recibido = Decimal('0.00')
        cambio = Decimal('0.00')
        pago_tipo = "N/A" 
    else:
        if pago_tipo == "Efectivo" and pago_recibido < total_final:
            messagebox.showwarning("Advertencia", "El monto recibido es menor al total.")
            return
        cambio = pago_recibido - total_final if pago_tipo == "Efectivo" else Decimal('0.00')
    
    descuento_monto = subtotal_sin_descuento * (descuento_porcentaje / Decimal('100'))

    cliente_id = combo_cliente.get().split(" - ")[0] if combo_cliente.get() and " - " in combo_cliente.get() else None
    cliente_nombre = entry_cliente_otro.get()
    if not cliente_nombre:
        cliente_nombre = next((c[1] for c in clientes if str(c[0])==cliente_id), "Público General")


    conexion = conectar_db()
    if conexion is None:
        return
    cursor = conexion.cursor()
    try:
        sql_venta = """
        INSERT INTO VENTAS (FECHA_HORA, ID_CLIENTE, NOMBRE_CLIENTE, TIPO_VENTA, MONTO_TOTAL, DESCUENTO, PAGO_TIPO, PAGO_RECIBIDO)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """
        cursor.execute(sql_venta, (
            datetime.now(),
            cliente_id,
            cliente_nombre,
            tipo_venta,
            float(total_final),
            float(descuento_porcentaje),
            pago_tipo,
            float(pago_recibido)
        ))
        id_venta = cursor.lastrowid

        productos_ticket = []
        for fila in filas_productos:
            producto_id = fila["combo"].get()
            if not producto_id:
                continue
            cantidad = int(fila["cant"].get() or 0)
            if cantidad == 0:
                continue
            
            # Determinar precio unitario y descripción para registro
            if producto_id == '0000':
                precio_unitario_float = float(Decimal(fila["precio_entry"].get() or '0.00'))
                descripcion_producto = fila["desc"] 
                clasificacion_producto = fila["clas"] 
            else:
                precio_unitario_float = float(fila["precio"]) if isinstance(fila["precio"], Decimal) else float(str(fila["precio"]))
                descripcion_producto = fila["desc"]
                clasificacion_producto = fila["clas"]
            
            subtotal = precio_unitario_float * cantidad
            
            cursor.execute("""
                INSERT INTO VENTA_PRODUCTOS (ID_VENTA, ID_PRODUCTO, DESCRIPCION, CLASIFICACION, CANTIDAD, PRECIO_UNITARIO, PRECIO_TOTAL)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,(id_venta, producto_id, descripcion_producto, clasificacion_producto, cantidad, precio_unitario_float, subtotal))
            
            # AÑADIR EL ID_PRODUCTO al diccionario para usarlo en el ticket
            productos_ticket.append({
                'id_producto': producto_id, # <--- Nuevo campo
                'desc': descripcion_producto,
                'clas': clasificacion_producto, # Esto se sigue guardando en BD pero no se usa en el ticket
                'cant': cantidad,
                'precio': precio_unitario_float,
                'subtotal': subtotal
            })

        conexion.commit()
        generar_ticket(
            id_venta, 
            cliente_nombre, 
            productos_ticket, 
            float(subtotal_sin_descuento), 
            float(descuento_porcentaje),    
            float(descuento_monto),         
            float(total_final),             
            float(pago_recibido), 
            float(cambio), 
            pago_tipo
        )
        messagebox.showinfo("Éxito","Venta registrada correctamente")
        limpiar_campos()
    except Error as e:
        messagebox.showerror("Error", f"No se pudo registrar la venta: {e}")
    finally:
        cursor.close()
        conexion.close()

# --- Limpiar campos (se mantiene la lógica) ---
def limpiar_campos():
    combo_cliente.set("")
    entry_cliente_otro.delete(0, tk.END)
    
    for i, fila in enumerate(filas_productos):
        for widget in frame_productos.grid_slaves(row=i+1): 
             widget.grid_forget()

    filas_productos.clear()
    
    label_total.config(text="TOTAL: $0.00", foreground=ACCENT_COLOR)
    label_cambio.config(text="Cambio: $0.00", foreground=TEXT_DARK)
    entry_descuento.delete(0, tk.END)
    entry_pago.delete(0, tk.END)
    combo_tipo_venta.set("Contado")
    combo_pago.set("Efectivo")
    
    gestionar_tipo_venta()
    
    agregar_fila()

# --- 4. Botones de Acción (LEFT/BOTTOM) ---
actions_frame = ttk.Frame(left_frame, padding="0 10 0 0")
actions_frame.pack(fill="x", pady=10)

ttk.Button(actions_frame, text="Registrar Venta", command=registrar_venta, style='TButton').pack(fill="x", expand=True, padx=5)


# --- 5. BINDINGS FINALES E INICIALIZACIÓN ---

entry_descuento.bind("<KeyRelease>", lambda e: calcular_total())
combo_pago.bind("<<ComboboxSelected>>", lambda e: calcular_cambio())
entry_pago.bind("<KeyRelease>", lambda e: calcular_cambio())

combo_tipo_venta.bind("<<ComboboxSelected>>", gestionar_tipo_venta) 
gestionar_tipo_venta() 

# Inicialización: Agregar una fila de producto al iniciar
agregar_fila()

root.mainloop()