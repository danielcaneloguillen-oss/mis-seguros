import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Mis Seguros", page_icon="📑", layout="wide")

# Conexión con Google Sheets
url = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df = conn.read(spreadsheet=url, usecols=[0, 1, 2, 3, 4])
    return df.dropna(how="all")

df_seguros = cargar_datos()
df_seguros['Vencimiento'] = pd.to_datetime(df_seguros['Vencimiento']).dt.date

# --- DISEÑO DE CABECERA ---
st.title("📑 Mis Pólizas")
st.caption("Gestión simplificada • Diseño Claro y Moderno")

# --- CÁLCULO DE GASTOS Y ALERTAS ---
hoy = date.today()

# Convertimos la columna de texto a "Fecha" de verdad para que Python la entienda
df_seguros['Vencimiento'] = pd.to_datetime(df_seguros['Vencimiento'], errors='coerce').dt.date

# Calculamos el total de dinero (solo de las filas que tengan número)
total_anual = pd.to_numeric(df_seguros['Prima'], errors='coerce').sum()

# Contamos cuántos vencen en los próximos 30 días
df_proximos = df_seguros.dropna(subset=['Vencimiento'])
proximos_30 = len(df_proximos[(df_proximos['Vencimiento'] - hoy).map(lambda x: 0 <= x.days <= 30)])

# --- CONFIGURACIÓN DE ALERTAS (45 DÍAS) ---
hoy = date.today()
margen_aviso = hoy + timedelta(days=45)

# Limpiamos la columna de posibles espacios en blanco y forzamos el formato
df_seguros['Vencimiento'] = pd.to_datetime(df_seguros['Vencimiento'], dayfirst=True, errors='coerce')

# Creamos una columna auxiliar solo para el cálculo (sin horas, solo fecha)
df_seguros['Fecha_Clean'] = df_seguros['Vencimiento'].dt.date

# Filtramos los avisos usando la fecha limpia
df_alertas = df_seguros[
    (df_seguros['Fecha_Clean'] <= margen_aviso) & 
    (df_seguros['Fecha_Clean'] >= hoy)
].copy()

# --- SEMÁFORO VISUAL ---
if not df_alertas.empty:
    for _, fila in df_alertas.iterrows():
        dias_restantes = (fila['Fecha_Clean'] - hoy).days
        st.info(f"📅 **AVISO**: {fila['Seguro']} vence en {dias_restantes} días ({fila['Fecha_Clean']}).")

# --- MÉTRICAS GENERALES ---
total_anual = pd.to_numeric(df_seguros['Prima'], errors='coerce').sum()
m1, m2, m3 = st.columns(3)
m1.metric("Inversión Anual", f"{total_anual:,.2f} €")
m2.metric("Total Seguros", len(df_seguros))
m3.metric("Avisos activos (<45d)", len(df_alertas))

st.write("---")

# --- NAVEGACIÓN ---
pestana1, pestana2 = st.tabs(["🔍 Ver Mis Seguros", "➕ Nueva Alta"])

with pestana1:
    if not df_seguros.empty:
        st.dataframe(
            df_seguros.sort_values("Vencimiento"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Enlace_Doc": st.column_config.LinkColumn("📄 Documento"),
                "Prima": st.column_config.NumberColumn("Cuota Anual", format="%.2f €"),
                "Vencimiento": st.column_config.DateColumn("Vence el", format="DD/MM/YYYY")
            }
        )
        with st.expander("⚙️ Gestión de Póliza Seleccionada"):
            sel = st.selectbox("Elegir póliza:", df_seguros['Seguro'].unique())
            idx = df_seguros[df_seguros['Seguro'] == sel].index[0]
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Renovar (+1 año)", use_container_width=True):
                    df_seguros.at[idx, 'Vencimiento'] = str(df_seguros.at[idx, 'Vencimiento'] + timedelta(days=365))
                    conn.update(spreadsheet=url, data=df_seguros)
                    st.rerun()
            with c2:
                if st.button("🗑️ Dar de Baja", type="primary", use_container_width=True):
                    df_final = df_seguros.drop(idx)
                    conn.update(spreadsheet=url, data=df_final)
                    st.rerun()
    else:
        st.info("No hay datos. Ve a 'Nueva Alta' para añadir tu primer seguro.")

with pestana2:
    st.subheader("Registrar nueva póliza")
    with st.form("alta", clear_on_submit=True):
        f1, f2 = st.columns(2)
        with f1:
            nombre = st.text_input("Seguro (ej. Coche)")
            cia = st.text_input("Compañía")
        with f2:
            cuota = st.number_input("Importe (€)", min_value=0.0)
            fecha = st.date_input("Vencimiento")
        link = st.text_input("Enlace al documento (Drive/Dropbox)")
        if st.button("Registrar en la Nube"):
    # 1. Cargamos los datos actuales para estar seguros de la estructura
    df_actual = cargar_datos()
    
    # 2. Creamos la fila nueva con los nombres de columna EXACTOS del Excel
    # Asegúrate de que estos nombres coincidan con tus títulos en Google Sheets
    nueva_fila = pd.DataFrame([{
        "Seguro": nombre,
        "Compania": cia,
        "Prima": cuota,
        "Vencimiento": str(fecha),
        "Enlace_Doc": link
    }])
    
    # 3. Concatenamos (unimos) la fila nueva
    df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
    
    # 4. Limpiamos cualquier columna extra que se haya colado antes de subir
    # Solo nos quedamos con las 5 columnas originales
    columnas_ok = ["Seguro", "Compania", "Prima", "Vencimiento", "Enlace_Doc"]
    df_final = df_final[columnas_ok]
    
    # 5. Subimos a Google Sheets
    conn.update(spreadsheet=url, worksheet="Hoja1", data=df_final)
    
    st.success("✅ ¡Seguro guardado correctamente!")
    st.balloons()
