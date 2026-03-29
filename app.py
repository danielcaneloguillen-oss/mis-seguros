import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Mis Seguros", page_icon="📑", layout="wide")

# --- CONEXIÓN CON GOOGLE SHEETS ---
url = st.secrets["connections"]["gsheets"]["spreadsheet"]
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    # Esta versión es mucho más sencilla y directa
    df = conn.read(spreadsheet=url)
    return df.dropna(how="all")

# --- CARGA Y LIMPIEZA INICIAL ---
df_seguros = cargar_datos()

# Limpiamos las fechas nada más leerlas (Día primero)
df_seguros['Vencimiento'] = pd.to_datetime(df_seguros['Vencimiento'], dayfirst=True, errors='coerce').dt.date

# --- DISEÑO DE CABECERA ---
st.title("📑 Mis Pólizas")
st.caption("Gestión de vencimientos con aviso de 45 días")

# --- LÓGICA DE ALERTAS (45 DÍAS) ---
hoy = date.today()
margen_aviso = hoy + timedelta(days=45)

# Filtramos los que vencen pronto (basándonos en la fecha ya limpia)
df_alertas = df_seguros[
    (df_seguros['Vencimiento'] <= margen_aviso) & 
    (df_seguros['Vencimiento'] >= hoy)
].copy()

# --- SEMÁFORO VISUAL ---
if not df_alertas.empty:
    for _, fila in df_alertas.iterrows():
        dias_restantes = (fila['Vencimiento'] - hoy).days
        if dias_restantes <= 7:
            st.error(f"🚨 **URGENTE**: {fila['Seguro']} vence en {dias_restantes} días ({fila['Vencimiento']}).")
        elif dias_restantes <= 15:
            st.warning(f"⚠️ **ATENCIÓN**: {fila['Seguro']} vence en {dias_restantes} días.")
        else:
            st.info(f"📅 **AVISO**: {fila['Seguro']} vence en {dias_restantes} días.")

# --- MÉTRICAS GENERALES ---
total_anual = pd.to_numeric(df_seguros['Prima'], errors='coerce').sum()
m1, m2, m3 = st.columns(3)
m1.metric("Inversión Anual", f"{total_anual:,.2f} €")
m2.metric("Total Seguros", len(df_seguros))
m3.metric("Avisos activos", len(df_alertas))

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
            sel = st.selectbox("Elegir póliza para renovar o borrar:", df_seguros['Seguro'].unique())
            idx = df_seguros[df_seguros['Seguro'] == sel].index[0]
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🔄 Renovar (+1 año)", use_container_width=True):
                    nueva_fecha = df_seguros.at[idx, 'Vencimiento'] + timedelta(days=365)
                    df_seguros.at[idx, 'Vencimiento'] = nueva_fecha
                    conn.update(spreadsheet=url, worksheet="Hoja1", data=df_seguros)
                    st.success("Renovado. Refrescando...")
                    st.rerun()
            with c2:
                if st.button("🗑️ Dar de Baja", type="primary", use_container_width=True):
                    df_final = df_seguros.drop(idx)
                    conn.update(spreadsheet=url, worksheet="Hoja1", data=df_final)
                    st.success("Eliminado. Refrescando...")
                    st.rerun()
    else:
        st.info("No hay datos en 'Hoja1'.")

with pestana2:
    st.subheader("Registrar nueva póliza")
    with st.form("formulario_alta", clear_on_submit=True):
        f1, f2 = st.columns(2)
        with f1:
            nombre = st.text_input("Seguro (ej. Coche)")
            cia = st.text_input("Compañía")
        with f2:
            cuota = st.number_input("Importe (€)", min_value=0.0)
            fecha_alta = st.date_input("Vencimiento", value=hoy)
        
        link = st.text_input("Enlace al documento (Drive/Dropbox)")
        
        # El botón de enviar
        boton_enviar = st.form_submit_button("Registrar en la Nube")
        
        if boton_enviar:
            if nombre and cia:
                # 1. Cargamos datos frescos para no sobreescribir
                df_actual = cargar_datos()
                
                # 2. Creamos la nueva fila
                nueva_fila = pd.DataFrame([{
                    "Seguro": nombre,
                    "Compania": cia,
                    "Prima": cuota,
                    "Vencimiento": fecha_alta,
                    "Enlace_Doc": link
                }])
                
                # 3. Unimos los datos antiguos con el nuevo
                df_final = pd.concat([df_actual, nueva_fila], ignore_index=True)
                
                # 4. Forzamos que solo se guarden estas 5 columnas
                columnas_ok = ["Seguro", "Compania", "Prima", "Vencimiento", "Enlace_Doc"]
                df_final = df_final[columnas_ok]
                
                # 5. GUARDADO CRÍTICO: Forzamos el nombre de la hoja que acabas de cambiar
                conn.update(spreadsheet=url, data=df_final)
                
                # 6. LIMPIEZA DE MEMORIA (Para que aparezca al instante)
                st.cache_data.clear() 
                st.success(f"✅ ¡{nombre} guardado correctamente!")
                st.balloons()
                st.rerun() 
            else:
                st.error("Por favor, rellena al menos el nombre y la compañía.")
