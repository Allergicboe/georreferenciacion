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
    copiando las columnas A (Fecha), B (Año), C (Mes) y D (Día) de la fila encontrada.
    Luego se actualiza la nueva fila usando update_cells con USER_ENTERED.
    Si no existe la fecha, se agrega una nueva fila al final.
    """
    fecha_str = fecha.strftime("%d-%m-%Y")
    fila_existente = buscar_ultima_fila_por_fecha(fecha_str)
    
    # Valores de las columnas A-D a copiar o generar
    fecha_val = fecha_str
    anio_val = fecha.strftime("%Y")
    mes_val = fecha.strftime("%m")
    dia_val = fecha.strftime("%d")
    
    if fila_existente:
        # Si ya existe la fecha, obtenemos la fila y copiamos A-D
        existing_row = hoja_datos.row_values(fila_existente)
        if len(existing_row) >= 1 and existing_row[0]:
            fecha_val = existing_row[0]
        if len(existing_row) >= 2 and existing_row[1]:
            anio_val = existing_row[1]
        if len(existing_row) >= 3 and existing_row[2]:
            mes_val = existing_row[2]
        if len(existing_row) >= 4 and existing_row[3]:
            dia_val = existing_row[3]
        
        # Insertar una fila vacía justo debajo de la última ocurrencia
        nueva_pos = fila_existente + 1
        hoja_datos.insert_row([""] * 9, nueva_pos)
        
        # Construir la nueva fila con los datos a insertar
        new_values = [fecha_val, anio_val, mes_val, dia_val, nombre, prod_serv, precio, "", ""]
        # Obtener el rango de celdas correspondiente a la nueva fila
        cells = hoja_datos.range(nueva_pos, 1, nueva_pos, len(new_values))
        for i, cell in enumerate(cells):
            cell.value = new_values[i]
        hoja_datos.update_cells(cells, value_input_option='USER_ENTERED')
    else:
        # Si no existe la fecha, se crea una nueva fila completa
        nueva_fila = [fecha_val, anio_val, mes_val, dia_val, nombre, prod_serv, precio, "", ""]
        hoja_datos.append_row(nueva_fila, value_input_option='USER_ENTERED')

def agregar_o_actualizar_ingreso(fecha, ingreso, razon):
    """
    Agrega ingresos en la hoja "Datos".
    Si ya existe una fila con la fecha seleccionada, se inserta una nueva fila debajo de la última ocurrencia,
    copiando las columnas A (Fecha), B (Año), C (Mes) y D (Día) de la fila encontrada.
    Luego se actualiza la nueva fila usando update_cells con USER_ENTERED.
    Si no existe la fecha, se agrega una nueva fila al final.
    """
    fecha_str = fecha.strftime("%d-%m-%Y")
    fila_existente = buscar_ultima_fila_por_fecha(fecha_str)
    
    fecha_val = fecha_str
    anio_val = fecha.strftime("%Y")
    mes_val = fecha.strftime("%m")
    dia_val = fecha.strftime("%d")
    
    if fila_existente:
        existing_row = hoja_datos.row_values(fila_existente)
        if len(existing_row) >= 1 and existing_row[0]:
            fecha_val = existing_row[0]
        if len(existing_row) >= 2 and existing_row[1]:
            anio_val = existing_row[1]
        if len(existing_row) >= 3 and existing_row[2]:
            mes_val = existing_row[2]
        if len(existing_row) >= 4 and existing_row[3]:
            dia_val = existing_row[3]
        
        nueva_pos = fila_existente + 1
        hoja_datos.insert_row([""] * 9, nueva_pos)
        
        new_values = [fecha_val, anio_val, mes_val, dia_val, "", "", "", ingreso, razon]
        cells = hoja_datos.range(nueva_pos, 1, nueva_pos, len(new_values))
        for i, cell in enumerate(cells):
            cell.value = new_values[i]
        hoja_datos.update_cells(cells, value_input_option='USER_ENTERED')
    else:
        nueva_fila = [fecha_val, anio_val, mes_val, dia_val, "", "", "", ingreso, razon]
        hoja_datos.append_row(nueva_fila, value_input_option='USER_ENTERED')

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
