import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

st.title("Análise e Relatório")

uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.subheader("Prévia dos Dados")
    st.dataframe(df)

    st.subheader("Opções de Análise")
    st.write(df.describe())

    st.subheader("Gráfico de Barras")
    # Exemplo: gráfico de barras agrupando pela primeira coluna categórica achada e valor da primeira numérica
    col_cat = st.selectbox("Coluna categórica (exemplo para agrupar):", df.select_dtypes(include='object').columns)
    col_num = st.selectbox("Coluna numérica (exemplo para valores):", df.select_dtypes(include='number').columns)

    grouped = df.groupby(col_cat)[col_num].sum().reset_index()
    fig, ax = plt.subplots()
    sns.barplot(x=col_cat, y=col_num, data=grouped, ax=ax)
    st.pyplot(fig)

    st.subheader("Mapa de Calor")
    cols = st.multiselect("Selecione colunas numéricas para o mapa de calor:", df.select_dtypes(include='number').columns)
    if cols and len(cols) > 1:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.heatmap(df[cols].corr(), annot=True, cmap='RdYlGn', ax=ax)
        st.pyplot(fig)
    else:
        st.info("Selecione ao menos duas colunas numéricas para o mapa de calor.")

