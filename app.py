import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import folium
from streamlit_folium import st_folium

# Configuração da página
st.set_page_config(layout="wide", page_title="Análise Completa com KPIs, Filtros Temporais e Mapas")

st.title("Dashboard de Análise Operacional Completo")

# Função de cache para o carregamento do arquivo
@st.cache_data
def load_data(uploaded_file):
    return pd.read_excel(uploaded_file)

uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])

if uploaded_file is not None:
    df = load_data(uploaded_file)

    # Conversão de colunas com data se existirem
    for col in df.columns:
        if 'date' in col.lower() or 'data' in col.lower() or 'hora' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

    st.subheader("Prévia dos Dados")
    st.dataframe(df)

    # Identificação de tipos de colunas
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()
    date_cols = df.select_dtypes(include='datetime').columns.tolist()

    # --- FILTROS DINÂMICOS, INCLUINDO TEMPORAIS ---
    st.sidebar.header("Filtros")
    df_filtered = df.copy()

    # Filtro temporal, se houver colunas de data
    if date_cols:
        date_col = st.sidebar.selectbox("Coluna de data para filtro temporal", date_cols)
        min_date = df[date_col].min()
        max_date = df[date_col].max()
        selected_date_range = st.sidebar.date_input("Período", [min_date, max_date])
        if len(selected_date_range) == 2:
            start_date, end_date = selected_date_range
            df_filtered = df_filtered[
                (df_filtered[date_col] >= pd.to_datetime(start_date)) &
                (df_filtered[date_col] <= pd.to_datetime(end_date))
            ]

    # Filtros categóricos
    for col in cat_cols:
        options = st.sidebar.multiselect(f"Filtrar {col}", options=df[col].unique(), default=df[col].unique())
        df_filtered = df_filtered[df_filtered[col].isin(options)]

    # Filtros numéricos (CORRETO: usar selected_range[0] e selected_range[1])
    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.sidebar.slider(
            f"Filtrar intervalo {col}", min_val, max_val, (min_val, max_val)
        )
        df_filtered = df_filtered[
            (df_filtered[col] >= selected_range[0]) & (df_filtered[col] <= selected_range[1])
        ]

    st.subheader("Dados após filtros")
    st.dataframe(df_filtered)

    # Botão para baixar dados filtrados
    st.download_button(
        "Baixar dados filtrados",
        df_filtered.to_csv(index=False).encode("utf-8"),
        "dados_filtrados.csv",
        "text/csv"
    )

    # --- KPIs em cards ---
    st.subheader("KPIs Principais")
    st.markdown("O painel abaixo mostra os principais indicadores estatísticos das colunas numéricas após filtragem dos dados.")
    if len(num_cols) > 0 and not df_filtered.empty:
        cols_kpi = st.columns(min(len(num_cols), 5))
        for i, col in enumerate(num_cols):
            media = df_filtered[col].mean()
            mediana = df_filtered[col].median()
            soma = df_filtered[col].sum()
            with cols_kpi[i % 5]:
                st.metric(label=f"{col} - Média", value=f"{media:.2f}")
                st.metric(label=f"{col} - Mediana", value=f"{mediana:.2f}")
                st.metric(label=f"{col} - Soma", value=f"{soma:.2f}")
    else:
        st.info("Sem dados numéricos ou dados filtrados vazios para KPIs.")

    # --- Visualizações tradicionais ---
    st.subheader("Histogramas e Boxplots")
    st.markdown("Utilize a caixa de seleção para visualizar a distribuição dos dados filtrados.")
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
    st.markdown("Resuma informações agrupando por colunas categóricas selecionadas.")
    if cat_cols and num_cols:
        group_col = st.selectbox("Coluna categórica para agrupamento", cat_cols)
        num_col_group = st.selectbox("Coluna numérica para resumo", num_cols)
        grouped = df_filtered.groupby(group_col)[num_col_group].agg(['count', 'sum', 'mean', 'median', 'std']).reset_index()
        st.dataframe(grouped)
    else:
        st.info("Sem colunas adequadas para agrupamento.")

    # --- ALERTAS DE MANUTENÇÃO BASEADOS EM HORIMETRO ---
    st.subheader("Alertas de Manutenção")
    st.markdown("Alerta equipamentos com horímetro acima de um valor definido e status de manutenção pendente ou agendado.")
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
            (df_filtered[manut_col].str.lower().isin([s.lower() for s in status_alerta]))
        ]

        if not alerta_df.empty:
            st.warning(
                f"Existem {len(alerta_df)} equipamentos com alerta de manutenção "
                f"(Horímetro >= {limite_horimetro} e manutenção nos status: {', '.join(status_alerta)})."
            )
            st.dataframe(alerta_df[[horimetro_col, manut_col] + cat_cols])
            st.download_button(
                "Baixar alertas de manutenção",
                alerta_df.to_csv(index=False).encode("utf-8"),
                "alertas_manutencao.csv",
                "text/csv"
            )
        else:
            st.success("Nenhum alerta de manutenção pendente encontrado.")
    else:
        st.info("Colunas para alertas de manutenção ou horímetro não encontradas no dataset.")

    # --- MAPA INTERATIVO PARA DADOS GEOGRÁFICOS (SE TIVER) ---
    st.subheader("Mapa Interativo")
    st.markdown(
        "Visualize geograficamente os registros presentes na planilha. "
        "O mapa interativo exibe a posição dos equipamentos, se latitude e longitude estiverem presentes."
    )
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

else:
    st.info("Por favor, faça o upload de uma planilha Excel para análise.")
