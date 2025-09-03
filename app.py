import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# Configuração da página
st.set_page_config(layout="wide", page_title="Análise Completa com KPIs, Filtros e Mapas Interativos")

st.title("Dashboard de Análise Operacional")

# Cache para leitura do Excel com todas as sheets
@st.cache_data(show_spinner=True)
def load_excel(file):
    xls = pd.ExcelFile(file)
    return {sheet: xls.parse(sheet) for sheet in xls.sheet_names}

# Cache para pré-processar dataframe: datetime conversion etc.
@st.cache_data
def preprocess_df(df):
    for col in df.columns:
        if 'date' in col.lower() or 'data' in col.lower() or 'hora' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df

# Cache para aplicar filtros numéricos e categóricos
@st.cache_data
def apply_filters(df, cat_filters, num_filters, date_col=None, date_range=None):
    df_filtered = df.copy()
    # Aplicar filtro data
    if date_col and date_range:
        df_filtered = df_filtered[
            (df_filtered[date_col] >= pd.to_datetime(date_range[0])) & 
            (df_filtered[date_col] <= pd.to_datetime(date_range[1]))
        ]
    # Aplicar filtros categóricos
    for col, values in cat_filters.items():
        if values:
            df_filtered = df_filtered[df_filtered[col].isin(values)]
    # Aplicar filtros numéricos
    for col, (min_v, max_v) in num_filters.items():
        df_filtered = df_filtered[(df_filtered[col]>=min_v) & (df_filtered[col]<=max_v)]
    return df_filtered

# Carregar arquivo Excel
uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])

if uploaded_file is not None:
    all_sheets = load_excel(uploaded_file)
    sheet_names = list(all_sheets.keys())

    sheet_selected = st.selectbox("Selecione a aba da planilha para análise", sheet_names)
    df = preprocess_df(all_sheets[sheet_selected])

    st.subheader(f"Visualização da aba: {sheet_selected}")
    st.dataframe(df)

    # Identificação tipos colunas
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()
    date_cols = df.select_dtypes(include='datetime').columns.tolist()

    # Sidebar - filtros
    st.sidebar.header("Filtros")
    # Filtro data (se existir)
    date_col = None
    date_range = None
    if date_cols:
        date_col = st.sidebar.selectbox("Coluna de data para filtro", date_cols)
        min_date, max_date = df[date_col].min(), df[date_col].max()
        date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])

    # Filtros categóricos
    cat_filters = {}
    for col in cat_cols:
        options = st.sidebar.multiselect(f"Filtrar {col}", options=df[col].dropna().unique(), default=df[col].dropna().unique())
        cat_filters[col] = options

    # Filtros numéricos
    num_filters = {}
    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.sidebar.slider(f"Intervalo {col}", min_val, max_val, (min_val, max_val))
        num_filters[col] = selected_range

    # Aplicar filtros com cache
    df_filtered = apply_filters(df, cat_filters, num_filters, date_col, date_range)

    st.subheader(f"Dados após filtros ({len(df_filtered)} registros)")
    st.dataframe(df_filtered)

    # Download dos dados filtrados
    st.download_button(
        label="Baixar dados filtrados",
        data=df_filtered.to_csv(index=False).encode('utf-8'),
        file_name=f"dados_filtrados_{sheet_selected}.csv",
        mime="text/csv"
    )

    # KPIs com plotly - média, mediana e soma para cada numérico
    if num_cols and not df_filtered.empty:
        st.subheader("KPIs Principais")
        kpi_data = []
        for col in num_cols:
            kpi_data.append({
                "Métrica": col,
                "Média": df_filtered[col].mean(),
                "Mediana": df_filtered[col].median(),
                "Soma": df_filtered[col].sum()
            })
        kpi_df = pd.DataFrame(kpi_data)
        st.dataframe(kpi_df.style.format({"Média": "{:.2f}", "Mediana": "{:.2f}", "Soma": "{:.2f}"}))

    # Visualizações com plotly para interatividade
    if num_cols and not df_filtered.empty:
        st.subheader("Visualizações Interativas")
        selected_num = st.selectbox("Selecione coluna numérica para análise gráfica", num_cols)
        fig_hist = px.histogram(df_filtered, x=selected_num, marginal="box", nbins=30, title=f"Histograma e Boxplot de {selected_num}")
        st.plotly_chart(fig_hist, use_container_width=True)

    # Agrupamento estatístico
    if cat_cols and num_cols:
        st.subheader("Agrupamento e Resumo Estatístico")
        group_col = st.selectbox("Coluna categórica para agrupamento", cat_cols)
        num_col_group = st.selectbox("Coluna numérica para resumo", num_cols)
        grouped = df_filtered.groupby(group_col)[num_col_group].agg(['count','sum','mean','median','std']).reset_index()
        st.dataframe(grouped.style.format({"sum": "{:.2f}", "mean": "{:.2f}", "median": "{:.2f}", "std": "{:.2f}"}))

    # Alertas de manutenção (verificar colunas para horímetro e status de manutenção)
    st.subheader("Alertas de Manutenção")
    manut_cols = [col for col in df_filtered.columns if 'manut' in col.lower()]
    horimetro_cols = [col for col in df_filtered.columns if 'horimet' in col.lower()]

    if manut_cols and horimetro_cols:
        horimetro_col = horimetro_cols[0]
        manut_col = manut_cols[0]
        limite_horimetro = st.sidebar.number_input("Horímetro mínimo para alerta", min_value=0, value=1000)
        status_alerta = st.sidebar.multiselect(
            "Status de manutenção para alerta",
            ['sim', 'pendente', 'agendar'],
            default=['pendente', 'agendar']
        )
        alerta_df = df_filtered[
            (df_filtered[horimetro_col] >= limite_horimetro) &
            (df_filtered[manut_col].fillna('').astype(str).str.lower().isin([s.lower() for s in status_alerta]))
        ]
        if not alerta_df.empty:
            st.warning(f"Existem {len(alerta_df)} equipamentos com alerta de manutenção (Horímetro >= {limite_horimetro} e status nos selecionados).")
            st.dataframe(alerta_df[[horimetro_col, manut_col] + cat_cols])
            st.download_button(
                label="Baixar alertas de manutenção",
                data=alerta_df.to_csv(index=False).encode('utf-8'),
                file_name="alertas_manutencao.csv",
                mime="text/csv"
            )
        else:
            st.success("Nenhum alerta de manutenção pendente encontrado.")
    else:
        st.info("Colunas para alertas de manutenção ou horímetro não encontradas no dataset.")

    # Mapa interativo para colunas geográficas (latitude e longitude)
    st.subheader("Mapa Interativo")
    lat_candidates = [col for col in df.columns if 'lat' in col.lower()]
    lon_candidates = [col for col in df.columns if 'lon' in col.lower() or 'long' in col.lower()]
    if lat_candidates and lon_candidates:
        lat_col = lat_candidates[0]
        lon_col = lon_candidates[0]
        map_data = df_filtered[[lat_col, lon_col]].dropna()
        if not map_data.empty:
            m = folium.Map(location=[map_data[lat_col].mean(), map_data[lon_col].mean()], zoom_start=10)
            for _, row in map_data.iterrows():
                folium.CircleMarker(
                    location=[row[lat_col], row[lon_col]],
                    radius=5,
                    color='blue',
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)
            st_folium(m, width=700, height=450)
        else:
            st.info("Não há dados geográficos disponíveis após filtro.")
    else:
        st.info("Colunas para latitude e longitude não encontradas no dataset.")

else:
    st.info("Por favor, faça o upload de uma planilha Excel para análise.")

