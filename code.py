import streamlit as st
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

# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
def buscar_fila_por_fecha(fecha_str):
    """
    Busca en la columna A de la hoja "Datos" la fila que contenga la fecha indicada (formato DD-MM-YYYY).
    Retorna el índice de la fila (1-indexado) si se encuentra, o None en caso contrario.
    """
    fechas = hoja_datos.col_values(1)
    for idx, valor in enumerate(fechas[1:], start=2):  # se asume que la primera fila es encabezado
        if valor == fecha_str:
            return idx
    return None

# -------------------------------
# FUNCIONES PARA ACTUALIZAR DATOS
# -------------------------------
def agregar_o_actualizar_dato(fecha, nombre, prod_serv, precio):
    """
    Actualiza o agrega datos en la hoja "Datos" para Producto/Servicio:
      - Identifica la fila por la fecha (columna A) en formato DD-MM-YYYY.
      - Actualiza o agrega los siguientes campos:
          E) Nombre
          F) Producto/Servicio
          G) Precio
    """
    fecha_str = fecha.strftime("%d-%m-%Y")
    fila_existente = buscar_fila_por_fecha(fecha_str)
    
    if fila_existente:
        # Actualiza únicamente las columnas E, F y G
        hoja_datos.update_cell(fila_existente, 5, nombre)      # Columna E: Nombre
        hoja_datos.update_cell(fila_existente, 6, prod_serv)     # Columna F: Producto/Servicio
        hoja_datos.update_cell(fila_existente, 7, precio)        # Columna G: Precio
    else:
        # Se agrega una nueva fila: se completa la columna A con la fecha y las columnas E, F y G
        nueva_fila = [fecha_str, "", "", "", nombre, prod_serv, precio, "", ""]
        hoja_datos.append_row(nueva_fila)

def agregar_o_actualizar_ingreso(fecha, ingreso, razon):
    """
    Actualiza o agrega ingresos en la hoja "Datos":
      - Identifica la fila por la fecha (columna A) en formato DD-MM-YYYY.
      - Actualiza o agrega el valor del Ingreso (columna H) y la Razón (columna I).
    """
    fecha_str = fecha.strftime("%d-%m-%Y")
    fila_existente = buscar_fila_por_fecha(fecha_str)
    
    if fila_existente:
        hoja_datos.update_cell(fila_existente, 8, ingreso)  # Columna H: Ingreso
        hoja_datos.update_cell(fila_existente, 9, razon)    # Columna I: Razón
    else:
        nueva_fila = [fecha_str, "", "", "", "", "", "", ingreso, razon]
        hoja_datos.append_row(nueva_fila)

# -------------------------------
# INTERFAZ DE USUARIO CON STREAMLIT
# -------------------------------
st.title("Gastos e Ingresos")

if st.button("Abrir Planilla"):
    st.markdown(f"[Ir a la Planilla]({sheet_url})", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["Gastos", "Ingresos"])

with tab1:
    st.header("Ingreso de Datos de Producto/Servicio")
    fecha = st.date_input("Selecciona la fecha", value=datetime.today())
    nombre = st.text_input("Nombre")
    prod_serv = st.selectbox("Selecciona Producto o Servicio", options=["Producto", "Servicio"])
    precio = st.text_input("Precio")
    
    if st.button("Enviar Datos", key="datos"):
        try:
            agregar_o_actualizar_dato(fecha, nombre, prod_serv, precio)
            st.success("Datos agregados/actualizados correctamente.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

with tab2:
    st.header("Ingreso de Ingresos")
    fecha_ingreso = st.date_input("Selecciona la fecha", key="fecha_ingreso", value=datetime.today())
    ingreso = st.text_input("Valor del Ingreso", key="valor_ingreso")
    razon = st.text_input("Razón", key="razon_ingreso")
    
    if st.button("Enviar Ingreso", key="ingreso"):
        try:
            agregar_o_actualizar_ingreso(fecha_ingreso, ingreso, razon)
            st.success("Ingreso agregado/actualizado correctamente.")
        except Exception as e:
            st.error(f"Ocurrió un error: {e}")