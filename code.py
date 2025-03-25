import streamlit as st
import streamlit.components.v1 as components  # Para renderizar HTML
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# -------------------------------
# CONFIGURACIÓN DE LA CONEXIÓN A GOOGLE SHEETS
# -------------------------------
scope = ['https://www.googleapis.com/auth/spreadsheets',
         'https://www.googleapis.com/auth/drive']

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope)

client = gspread.authorize(credentials)

sheet_url = st.secrets["sheet"]["url"]
# Seleccionar la hoja llamada "Datos"
hoja_datos = client.open_by_url(sheet_url).worksheet("Datos")

# Configuración de la página
st.set_page_config(
    page_title="Gastos e Ingresos",
    page_icon="⚙️",
    layout="wide"
)

# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
def buscar_ultima_fila_por_fecha(fecha_str):
    """
    Busca en la columna A de la hoja "Datos" todas las filas que contengan la fecha indicada (formato DD-MM-YYYY).
    Retorna el índice (1-indexado) de la última ocurrencia o None si no se encuentra.
    """
    fechas = hoja_datos.col_values(1)
    fila_encontrada = None
    # Se asume que la primera fila es encabezado, por eso se recorre desde la segunda fila
    for idx, valor in enumerate(fechas[1:], start=2):
        if valor == fecha_str:
            fila_encontrada = idx
    return fila_encontrada

# -------------------------------
# FUNCIONES PARA ACTUALIZAR DATOS
# -------------------------------
def agregar_o_actualizar_dato(fecha, nombre, prod_serv, precio):
    """
    Agrega datos en la hoja "Datos" para Producto/Servicio.
    Si ya existe una fila con la fecha seleccionada, se inserta una nueva fila debajo de la última ocurrencia,
    copiando las columnas A (Fecha), B (Año), C (Mes) y D (Día).
    Los datos nuevos se colocan en las columnas E, F y G.
    """
    fecha_str = fecha.strftime("%d-%m-%Y")
    fila_existente = buscar_ultima_fila_por_fecha(fecha_str)
    
    if fila_existente:
        # Obtener los valores de las columnas A-D de la fila encontrada
        existing_row = hoja_datos.row_values(fila_existente)
        fecha_val = existing_row[0] if len(existing_row) >= 1 else fecha_str
        anio_val = existing_row[1] if len(existing_row) >= 2 else fecha.strftime("%Y")
        mes_val = existing_row[2] if len(existing_row) >= 3 else fecha.strftime("%m")
        dia_val = existing_row[3] if len(existing_row) >= 4 else fecha.strftime("%d")
        
        # Eliminar apostrofe inicial en el mes (si lo hubiera)
        mes_val = mes_val.lstrip("'")
        
        # Crear la nueva fila copiando A-D y agregando los datos en E, F y G
        new_row = [fecha_val, anio_val, mes_val, dia_val, nombre, prod_serv, precio, "", ""]
        # Insertar la nueva fila justo debajo de la última fila encontrada
        hoja_datos.insert_row(new_row, fila_existente + 1)
    else:
        # Si no existe ninguna fila con esa fecha, se crea una nueva fila con los datos completos
        fecha_val = fecha.strftime("%d-%m-%Y")
        anio_val = fecha.strftime("%Y")
        mes_val = fecha.strftime("%m")
        dia_val = fecha.strftime("%d")
        nueva_fila = [fecha_val, anio_val, mes_val, dia_val, nombre, prod_serv, precio, "", ""]
        hoja_datos.append_row(nueva_fila)

def agregar_o_actualizar_ingreso(fecha, ingreso, razon):
    """
    Agrega ingresos en la hoja "Datos".
    Si ya existe una fila con la fecha seleccionada, se inserta una nueva fila debajo de la última ocurrencia,
    copiando las columnas A (Fecha), B (Año), C (Mes) y D (Día).
    Los nuevos datos se colocan en las columnas H (Ingreso) e I (Razón).
    """
    fecha_str = fecha.strftime("%d-%m-%Y")
    fila_existente = buscar_ultima_fila_por_fecha(fecha_str)
    
    if fila_existente:
        existing_row = hoja_datos.row_values(fila_existente)
        fecha_val = existing_row[0] if len(existing_row) >= 1 else fecha_str
        anio_val = existing_row[1] if len(existing_row) >= 2 else fecha.strftime("%Y")
        mes_val = existing_row[2] if len(existing_row) >= 3 else fecha.strftime("%m")
        dia_val = existing_row[3] if len(existing_row) >= 4 else fecha.strftime("%d")
        
        # Eliminar apostrofe inicial en el mes (si lo hubiera)
        mes_val = mes_val.lstrip("'")
        
        new_row = [fecha_val, anio_val, mes_val, dia_val, "", "", "", ingreso, razon]
        hoja_datos.insert_row(new_row, fila_existente + 1)
    else:
        fecha_val = fecha.strftime("%d-%m-%Y")
        anio_val = fecha.strftime("%Y")
        mes_val = fecha.strftime("%m")
        dia_val = fecha.strftime("%d")
        nueva_fila = [fecha_val, anio_val, mes_val, dia_val, "", "", "", ingreso, razon]
        hoja_datos.append_row(nueva_fila)

# -------------------------------
# INTERFAZ DE USUARIO CON STREAMLIT
# -------------------------------
st.title("Gastos e Ingresos")

# Botón HTML para ir a la planilla
html_button = f"""
<div style="text-align: left; margin-bottom: 10px;">
    <a href="{sheet_url}" target="_blank">
        <button style="
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 5px 10px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            border-radius: 5px;
            cursor: pointer;">
            Abrir Planilla de Google
        </button>
    </a>
</div>
"""
components.html(html_button, height=50)

tab1, tab2 = st.tabs(["Gastos", "Ingresos"])

with tab1:
    st.header("Ingreso de Gastos")
    fecha = st.date_input("Selecciona la fecha", value=datetime.today())
    nombre = st.text_input("Nombre")
    prod_serv = st.selectbox("Selecciona Producto o Servicio", options=["Producto", "Servicio"])
    precio = st.text_input("Precio")
    
    if st.button("Enviar Datos", key="datos"):
        try:
            agregar_o_actualizar_dato(fecha, nombre, prod_serv, precio)
            st.success("Datos agregados correctamente.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

with tab2:
    st.header("Ingreso de Ingresos")
    fecha_ingreso = st.date_input("Selecciona la fecha", key="fecha_ingreso", value=datetime.today())
    ingreso = st.text_input("Ingreso", key="valor_ingreso")
    razon = st.text_input("Razón", key="razon_ingreso")
    
    if st.button("Enviar Ingreso", key="ingreso"):
        try:
            agregar_o_actualizar_ingreso(fecha_ingreso, ingreso, razon)
            st.success("Ingreso agregado correctamente.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")
