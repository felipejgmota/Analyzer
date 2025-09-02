import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("Análise e Relatório de Excel - Completo com KPIs e Visualizações")

uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.subheader("Prévia dos Dados")
    st.dataframe(df)

    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()

    # --- FILTROS DINÂMICOS ---
    st.subheader("Filtros Dinâmicos")
    df_filtered = df.copy()

    for col in cat_cols:
        options = st.multiselect(f"Filtrar {col}", options=df[col].unique(), default=df[col].unique())
        df_filtered = df_filtered[df_filtered[col].isin(options)]

    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.slider(f"Filtrar intervalo {col}", min_val, max_val, (min_val, max_val))
        df_filtered = df_filtered[(df_filtered[col] >= selected_range[0]) & (df_filtered[col] <= selected_range[1])]

    st.subheader("Dados Filtrados")
    st.dataframe(df_filtered)

    # --- CARDS DE KPIs (Indicadores) ---
    st.subheader("Indicadores Principais (KPIs)")

    if len(num_cols) > 0 and not df_filtered.empty:
        cols = st.columns(len(num_cols))
        for i, col in enumerate(num_cols):
            media = df_filtered[col].mean()
            mediana = df_filtered[col].median()
            soma = df_filtered[col].sum()
            with cols[i]:
                st.metric(label=f"{col} - Média", value=f"{media:.2f}")
                st.metric(label=f"{col} - Mediana", value=f"{mediana:.2f}")
                st.metric(label=f"{col} - Soma", value=f"{soma:.2f}")
    else:
        st.info("Sem dados numéricos ou dados filtrados vazios para mostrar resumo.")

    # --- HISTOGRAMA E BOXPLOT ---
    st.subheader("Histogramas e Boxplots")
    if num_cols:
        col_hist = st.selectbox("Selecione coluna numérica para histograma e boxplot", num_cols)
        fig, axs = plt.subplots(1, 2, figsize=(14, 5))
        sns.histplot(df_filtered[col_hist], kde=True, ax=axs[0])
        axs[0].set_title(f"Histograma de {col_hist}")
        sns.boxplot(x=df_filtered[col_hist], ax=axs[1])
        axs[1].set_title(f"Boxplot de {col_hist}")
        st.pyplot(fig)
    else:
        st.info("Sem colunas numéricas para gráficos.")

    # --- AGRUPAMENTO E RESUMO ESTATÍSTICO ---
    st.subheader("Agrupamento e Resumo Estatístico")
    if cat_cols and num_cols:
        group_col = st.selectbox("Selecione coluna categórica para agrupar", cat_cols)
        num_col_group = st.selectbox("Selecione coluna numérica para resumir", num_cols)
        grouped = df_filtered.groupby(group_col)[num_col_group].agg(['count', 'sum', 'mean', 'median', 'std']).reset_index()
        st.dataframe(grouped)
    else:
        st.info("Sem colunas categóricas ou numéricas para agrupamento.")

    # --- NOVAS IDEIAS BASEADAS NOS ARQUIVOS ENVIADOS ---

    st.subheader("Visualizações Avançadas Baseadas no Conteúdo dos Relatórios")

    # Exemplo 1: KPIs de Desempenho Operacional como cards
    st.markdown("### KPIs Operacionais Exemplo")
    if set(['Área Operacional (ha)', 'Velocidade Média Efetiva (km/h)', 'Média de Consumo Médio (l/ha)']).issubset(df_filtered.columns):
        kpi_cols = ['Área Operacional (ha)', 'Velocidade Média Efetiva (km/h)', 'Média de Consumo Médio (l/ha)']
        cols_kpi = st.columns(len(kpi_cols))
        for i, col in enumerate(kpi_cols):
            valor = df_filtered[col].sum() if col == 'Área Operacional (ha)' else df_filtered[col].mean()
            with cols_kpi[i]:
                st.metric(label=col, value=f"{valor:.2f}")
    else:
        st.info("KPIs específicos para Área Operacional e Consumo não disponíveis nos dados filtrados.")

    # Exemplo 2: Análise de Eficiência por categoria (se existir essa coluna)
    if 'Eficiência de Motor (%)' in df_filtered.columns and cat_cols:
        st.markdown("### Eficiência de Motor (%) por categoria")
        cat_for_efficiency = st.selectbox("Selecione categoria para análise de eficiência", cat_cols)
        plt.figure(figsize=(10,6))
        sns.barplot(x=cat_for_efficiency, y='Eficiência de Motor (%)', data=df_filtered)
        plt.xticks(rotation=45)
        st.pyplot(plt.gcf())
    else:
        st.info("Coluna 'Eficiência de Motor (%)' ou categorias necessárias não disponíveis.")

    # Exemplo 3: Gráfico de área operacional por categoria, inspirado nos dashboards enviados
    if 'Área Operacional (ha)' in df_filtered.columns and cat_cols:
        st.markdown("### Área Operacional (ha) por Categoria")
        cat_for_area = st.selectbox("Selecione categoria para área operacional", cat_cols, key='area_oper')
        grouped_area = df_filtered.groupby(cat_for_area)['Área Operacional (ha)'].sum().reset_index()
        plt.figure(figsize=(10,6))
        sns.barplot(x=cat_for_area, y='Área Operacional (ha)', data=grouped_area)
        plt.xticks(rotation=45)
        st.pyplot(plt.gcf())
    else:
        st.info("Dados para área operacional por categoria não disponíveis.")

