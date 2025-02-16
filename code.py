import streamlit as st
import os
import gdown
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
from scipy.spatial import cKDTree
import gspread
from google.oauth2 import service_account
from concurrent.futures import ThreadPoolExecutor

# Configuración de la página
st.set_page_config(
    page_title="Georreferenciación de Campos",
    page_icon="🌍",
    layout="wide"
)

# Configuración de estilos
st.markdown("""
    <style>
    .stAlert {
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Enlaces de los archivos shape
file_urls = {
    "combined.shp": "https://drive.google.com/uc?id=1UBuvlHzBGV4CNArXTJsOUeu4kW-M4V1Z",
    "combined.dbf": "https://drive.google.com/uc?id=1sLEdQDHX3yKof2q7wjhH3R-yqACdit0g",
    "combined.prj": "https://drive.google.com/uc?id=1f7R7N6gs9en-RJr3vY21Gxjxesal6ZQg",
    "combined.shx": "https://drive.google.com/uc?id=1MfeWFsxlA7EUR3sxnC3WC--ukevrMei8"
}

# URL de Google Sheets
SPREADSHEET_URL = 'https://docs.google.com/spreadsheets/d/1_74Vt8KL0bscmSME5Evm6hn4DWytLdGDGb98tHyNwtc/edit?usp=drive_link'

@st.cache_resource
def download_shapefiles():
    """Descarga los archivos shape y retorna la ruta del directorio"""
    download_folder = os.path.join(os.getcwd(), "shapefile_downloaded")
    os.makedirs(download_folder, exist_ok=True)
    
    for filename, url in file_urls.items():
        destination = os.path.join(download_folder, filename)
        if not os.path.exists(destination):
            gdown.download(url, destination, quiet=True)
    
    return download_folder

@st.cache_resource
def load_shapefile(shapefile_path):
    """Carga el archivo shape"""
    return gpd.read_file(shapefile_path)

def vectorized_parse_coordinates(series):
    """Procesa las coordenadas de forma vectorizada"""
    series = pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce')
    mask = np.abs(series) > 180
    series[mask] = series[mask] / 100000000.0
    return series

def init_google_sheets():
    """Inicializa la conexión con Google Sheets"""
    # Crear credenciales desde los secretos de Streamlit
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    return gspread.authorize(credentials)

def process_data(data, gdf):
    """Procesa los datos y realiza la georreferenciación"""
    # Procesar coordenadas
    data['lat'] = vectorized_parse_coordinates(data['Latitud campo'])
    data['lon'] = vectorized_parse_coordinates(data['Longitud Campo'])
    
    # Identificar coordenadas inválidas
    invalid_mask = data['lat'].isna() | data['lon'].isna() | \
                  np.isinf(data['lat']) | np.isinf(data['lon'])
    valid_data = data[~invalid_mask].copy()
    
    # Crear array de centroides
    centroids = np.array([[geom.centroid.x, geom.centroid.y] for geom in gdf.geometry])
    tree = cKDTree(centroids)
    
    # Crear array de puntos válidos
    points = np.column_stack([valid_data['lon'].values, valid_data['lat'].values])
    
    # Encontrar el polígono más cercano
    distances, indices = tree.query(points, k=1)
    
    # Determinar puntos fuera del territorio
    DISTANCE_THRESHOLD = 1
    outside_mask = distances > DISTANCE_THRESHOLD
    
    # Crear DataFrame con resultados
    results = pd.DataFrame({
        'Region': gdf.iloc[indices]['Region'].values,
        'Provincia': gdf.iloc[indices]['Provincia'].values,
        'Comuna': gdf.iloc[indices]['Comuna'].values,
        'original_index': valid_data.index + 2
    })
    
    # Marcar puntos fuera como "OTROS"
    results.loc[outside_mask, ['Region', 'Provincia', 'Comuna']] = "OTROS"
    
    # Agregar filas con coordenadas inválidas
    na_results = pd.DataFrame({
        'Region': "NA",
        'Provincia': "NA",
        'Comuna': "NA",
        'original_index': data[invalid_mask].index + 2
    })
    
    final_results = pd.concat([results, na_results], ignore_index=True)
    return final_results, len(valid_data), len(data[invalid_mask])

def update_google_sheets(gc, final_results):
    """Actualiza Google Sheets con los resultados"""
    try:
        sheet = gc.open_by_url(SPREADSHEET_URL).sheet1
        
        # Preparar actualizaciones en lotes
        BATCH_SIZE = 1000
        updates = []
        current_batch = []
        
        for _, row in final_results.iterrows():
            current_batch.append({
                'range': f'H{row.original_index}:J{row.original_index}',
                'values': [[row.Region, row.Provincia, row.Comuna]]
            })
            
            if len(current_batch) >= BATCH_SIZE:
                updates.append(current_batch)
                current_batch = []
        
        if current_batch:
            updates.append(current_batch)
        
        # Actualizar en paralelo
        with ThreadPoolExecutor(max_workers=4) as executor:
            for batch in updates:
                sheet.batch_update(batch)
        
        return True
    except Exception as e:
        st.error(f"Error updating Google Sheets: {str(e)}")
        return False

def main():
    st.title("🌍 Geocoding App")
    st.write("Esta aplicación georreferencia automáticamente las ubicaciones desde Google Sheets")
    
    # Mostrar estado de la descarga de shapefiles
    with st.spinner("Descargando archivos shape..."):
        download_folder = download_shapefiles()
        shapefile_path = os.path.join(download_folder, "combined.shp")
        gdf = load_shapefile(shapefile_path)
        st.success("✅ Archivos shape cargados correctamente")
    
    # Inicializar Google Sheets
    if st.button("🚀 Iniciar Proceso", type="primary"):
        try:
            with st.spinner("Conectando con Google Sheets..."):
                gc = init_google_sheets()
                sheet = gc.open_by_url(SPREADSHEET_URL).sheet1
                data = pd.DataFrame(sheet.get_all_records())
                st.success(f"✅ Datos cargados: {len(data)} filas")
            
            # Procesar datos
            with st.spinner("Procesando datos..."):
                final_results, valid_count, invalid_count = process_data(data, gdf)
                
                # Mostrar estadísticas
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Registros", len(data))
                with col2:
                    st.metric("Coordenadas Válidas", valid_count)
                with col3:
                    st.metric("Casillas Inválidas", invalid_count)
            
            # Actualizar Google Sheets
            with st.spinner("Actualizando Google Sheets..."):
                if update_google_sheets(gc, final_results):
                    st.success("✅ Proceso completado exitosamente!")
                    
                    # Mostrar preview de resultados
                    st.subheader("📊 Previsualización de resultados")
                    st.dataframe(
                        final_results[['original_index', 'Region', 'Provincia', 'Comuna']]
                        .sort_values('original_index')
                        .head(10)
                    )
        
        except Exception as e:
            st.error(f"Error en el proceso: {str(e)}")

if __name__ == "__main__":
    main()
