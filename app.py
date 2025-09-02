import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Importa folium para mapa
import folium
from streamlit_folium import st_folium

# Configuração da página
st.set_page_config(layout="wide", page_title="Análise Completa com KPIs, Filtros Temporais e Mapas")

st.title("Dashboard de Análise Operacional Completo")

uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # Tentar converter colunas de data se existirem
    for col in df.columns:
        if 'date' in col.lower() or 'data' in col.lower() or 'hora' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

    st.subheader("Prévia dos Dados")
    st.dataframe(df)

    # Identificação básica de colunas por tipo
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()
    date_cols = df.select_dtypes(include='datetime').columns.tolist()

    # --- FILTROS DINÂMICOS, INCLUINDO TEMPORAIS ---
    st.sidebar.header("Filtros")

    df_filtered = df.copy()

    # Filtro temporal se houver colunas de data
    if date_cols:
        date_col = st.sidebar.selectbox("Coluna de data para filtro temporal", date_cols)
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        selected_date_range = st.sidebar.date_input("Período", [min_date, max_date])
        if len(selected_date_range) == 2:
            start_date, end_date = selected_date_range
            df_filtered = df_filtered[(df_filtered[date_col] >= pd.to_datetime(start_date)) & 
                                      (df_filtered[date_col] <= pd.to_datetime(end_date))]

    # Outros filtros categóricos e numéricos no sidebar
    for col in cat_cols:
        options = st.sidebar.multiselect(f"Filtrar {col}", options=df[col].unique(), default=df[col].unique())
        df_filtered = df_filtered[df_filtered[col].isin(options)]

    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.sidebar.slider(f"Filtrar intervalo {col}", min_val, max_val, (min_val, max_val))
        df_filtered = df_filtered[(df_filtered[col] >= selected_range[0]) & (df_filtered[col] <= selected_range[1])]

    st.subheader("Dados após filtros")
    st.dataframe(df_filtered)

    # --- KPIs em cards ---
    st.subheader("KPIs Principais")

    if len(num_cols) > 0 and not df_filtered.empty:
        cols_kpi = st.columns(len(num_cols))
        for i, col in enumerate(num_cols):
            media = df_filtered[col].mean()
            mediana = df_filtered[col].median()
            soma = df_filtered[col].sum()
            with cols_kpi[i]:
                st.metric(label=f"{col} - Média", value=f"{media:.2f}")
                st.metric(label=f"{col} - Mediana", value=f"{mediana:.2f}")
                st.metric(label=f"{col} - Soma", value=f"{soma:.2f}")
    else:
        st.info("Sem dados numéricos ou dados filtrados vazios para KPIs.")

    # --- Visualizações tradicionais ---
    st.subheader("Histogramas e Boxplots")
    if num_cols:
        col_hist = st.selectbox("Coluna numérica para histograma e boxplot", num_cols)
        fig, axs = plt.subplots(1, 2, figsize=(14, 5))
        sns.histplot(df_filtered[col_hist], kde=True, ax=axs[0])
        axs[0].set_title(f"Histograma de {col_hist}")
        sns.boxplot(x=df_filtered[col_hist], ax=axs[1])
        axs[1].set_title(f"Boxplot de {col_hist}")
        st.pyplot(fig)
    else:
        st.info("Sem colunas numéricas para gráficos.")

    # --- Agrupamento ---
    st.subheader("Agrupamento e Resumo Estatístico")
    if cat_cols and num_cols:
        group_col = st.selectbox("Coluna categórica para agrupamento", cat_cols)
        num_col_group = st.selectbox("Coluna numérica para resumo", num_cols)
        grouped = df_filtered.groupby(group_col)[num_col_group].agg(['count', 'sum', 'mean', 'median', 'std']).reset_index()
        st.dataframe(grouped)
    else:
        st.info("Sem colunas adequadas para agrupamento.")

    # --- ALERTAS DE MANUTENÇÃO BASEADOS EM HORIMETRO ---
    st.subheader("Alertas de Manutenção")

    # Exemplo básico: verificar colunas relacionadas a manutenção e horimetro
    manut_cols = [col for col in df_filtered.columns if 'manut' in col.lower()]  # Manutenção
    horimetro_cols = [col for col in df_filtered.columns if 'horimet' in col.lower()]

    if manut_cols and horimetro_cols:
        horimetro_col = horimetro_cols[0]
        manut_col = manut_cols[0]

        # Definir condição exemplo: horimetro acima de 1000 e manutenção pendente
        alerta_df = df_filtered[(df_filtered[horimetro_col] >= 1000) & (df_filtered[manut_col].str.lower().isin(['sim', 'pendente', 'agendar']))]

        if not alerta_df.empty:
            st.warning(f"Existem {len(alerta_df)} equipamentos com alerta de manutenção (Horímetro >= 1000 e manutenção pendente).")
            st.dataframe(alerta_df[[horimetro_col, manut_col] + cat_cols])
        else:
            st.success("Nenhum alerta de manutenção pendente encontrado.")
    else:
        st.info("Colunas para alertas de manutenção ou horímetro não encontradas.")

    # --- MAPA INTERATIVO PARA DADOS GEOGRÁFICOS (SE TIVER) ---
    st.subheader("Mapa Interativo")

    # Tenta identificar colunas geográficas comuns
    lat_candidates = [col for col in df.columns if 'lat' in col.lower()]
    lon_candidates = [col for col in df.columns if 'lon' in col.lower() or 'long' in col.lower()]

    if lat_candidates and lon_candidates:
        lat_col = lat_candidates[0]
        lon_col = lon_candidates[0]
        map_data = df_filtered[[lat_col, lon_col]].dropna()

        if not map_data.empty:
            m = folium.Map(location=[map_data[lat_col].mean(), map_data[lon_col].mean()], zoom_start=10)
            for idx, row in map_data.iterrows():
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
        st.info("Colunas geográficas (latitude/longitude) não encontradas no dataset.")

