import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Caso queira ativar autenticação futuramente, descomente:
# import streamlit_authenticator as stauth
# users = { ... } # Definição de usuários e senha aqui
# hashed_passwords = stauth.Hasher([...]).generate()
# credentials = {...}
# authenticator = stauth.Authenticate(credentials, "cookie_name", "signature_key", cookie_expiry_days=1)
# name, authentication_status, username = authenticator.login("Login", "main")

# if authentication_status:
#     st.write(f"Bem-vindo, {name}!")
# else:
#     st.warning("Por favor, faça login.")
#     st.stop()

st.title("Análise e Relatório de Excel - Completo")

uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.subheader("Prévia dos Dados")
    st.dataframe(df)

    # Filtros dinâmicos
    st.subheader("Filtros Dinâmicos")
    df_filtered = df.copy()

    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()

    for col in cat_cols:
        options = st.multiselect(f"Filtrar {col}", options=df[col].unique(), default=df[col].unique())
        df_filtered = df_filtered[df_filtered[col].isin(options)]

    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.slider(f"Filtrar intervalo {col}", min_val, max_val, (min_val, max_val))
        df_filtered = df_filtered[(df_filtered[col] >= selected_range[0]) & (df_filtered[col] <= selected_range[1])]

    st.subheader("Dados Filtrados")
    st.dataframe(df_filtered)

    # Histogramas e boxplots interativos
    st.subheader("Histogramas e Boxplots")
    if num_cols:
        col_hist = st.selectbox("Selecione coluna numérica para histograma e boxplot", num_cols)
        fig, axs = plt.subplots(1, 2, figsize=(12, 4))
        sns.histplot(df_filtered[col_hist], kde=True, ax=axs[0])
        axs[0].set_title(f"Histograma de {col_hist}")
        sns.boxplot(x=df_filtered[col_hist], ax=axs[1])
        axs[1].set_title(f"Boxplot de {col_hist}")
        st.pyplot(fig)
    else:
        st.info("Sem colunas numéricas para gráficos.")

    # Agrupamento e resumo estatístico
    st.subheader("Agrupamento e Resumo Estatístico")
    if cat_cols and num_cols:
        group_col = st.selectbox("Selecione coluna categórica para agrupar", cat_cols)
        num_col_group = st.selectbox("Selecione coluna numérica para resumir", num_cols)
        grouped = df_filtered.groupby(group_col)[num_col_group].agg(['count', 'sum', 'mean', 'median', 'std']).reset_index()
        st.dataframe(grouped)
    else:
        st.info("Sem colunas categóricas ou numéricas para agrupamento.")

    # Caso tenha autenticacao, adicionar botão de logout:
    # authenticator.logout("Logout", "sidebar")



