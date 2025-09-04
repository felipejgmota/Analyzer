import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import io

# PAGE CONFIG
st.set_page_config(layout="wide", page_title="Dashboard Operacional", initial_sidebar_state="expanded")
st.title("📊 Dashboard de Análise Operacional")

# ================ Utils and Data Loading ================
@st.cache_data(show_spinner=True)
def load_excel(file):
    xls = pd.ExcelFile(file)
    return {sheet: xls.parse(sheet) for sheet in xls.sheet_names}

@st.cache_data
def preprocess_df(df):
    for col in df.columns:
        if 'date' in col.lower() or 'data' in col.lower() or 'hora' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df

@st.cache_data
def apply_filters(df, cat_filters, num_filters, date_col=None, date_range=None):
    df_filtered = df.copy()
    if date_col and date_range:
        df_filtered = df_filtered[
            (df_filtered[date_col] >= pd.to_datetime(date_range[0]))
            & (df_filtered[date_col] <= pd.to_datetime(date_range[1]))
        ]
    for col, values in cat_filters.items():
        if values:
            df_filtered = df_filtered[df_filtered[col].isin(values)]
    for col, (min_v, max_v) in num_filters.items():
        df_filtered = df_filtered[(df_filtered[col] >= min_v) & (df_filtered[col] <= max_v)]
    return df_filtered

def export_pdf(df, title="Relatório Operacional"):
    # Exporta DataFrame para PDF simples usando reportlab
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(letter))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30, 550, title)
    c.setFont("Helvetica", 12)
    c.drawString(30, 530, f"Total registros: {len(df)}")
    x, y = 30, 500
    colnames = df.columns.tolist()
    col_h = [str(x)[:13] for x in colnames]
    c.drawString(30, y, " | ".join(col_h))
    y -= 18
    for i, row in df.iterrows():
        line = " | ".join([str(row[col])[:12] for col in colnames])
        c.drawString(x, y, line)
        y -= 18
        if y < 40:
            c.showPage()
            y = 520
    c.save()
    buf.seek(0)
    return buf

uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])

# =============== PREFERÊNCIAS E HISTÓRICO (Simples) ================
st.sidebar.subheader("Minhas Visões Favoritas")
if 'favoritos' not in st.session_state:
    st.session_state['favoritos'] = []
favorito = st.sidebar.text_input("Salvar filtros atuais como nome...")
if st.sidebar.button("Salvar visão favorita"):
    st.session_state['favoritos'].append(favorito)
if st.session_state['favoritos']:
    st.sidebar.write("Favoritos Salvos:")
    st.sidebar.write(st.session_state['favoritos'])

# ================ UPLOAD e PLANILHA ================
if uploaded_file is not None:
    all_sheets = load_excel(uploaded_file)
    sheet_names = list(all_sheets.keys())
    sheet_selected = st.selectbox("Selecione a aba para análise", sheet_names)
    df = preprocess_df(all_sheets[sheet_selected])
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()
    date_cols = df.select_dtypes(include='datetime').columns.tolist()

    # ====== Filtros Sidebar ======
    st.sidebar.header("Filtros Dinâmicos")
    date_col, date_range = None, None
    if date_cols:
        date_col = st.sidebar.selectbox("Coluna de data para filtro", date_cols)
        min_date, max_date = df[date_col].min(), df[date_col].max()
        date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
    cat_filters, num_filters, indicadores_custom = {}, {}, {}
    for col in cat_cols:
        options = st.sidebar.multiselect(f"Filtrar {col}", options=df[col].dropna().unique(), default=df[col].dropna().unique())
        cat_filters[col] = options
    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.sidebar.slider(f"Intervalo {col}", min_val, max_val, (min_val, max_val))
        num_filters[col] = selected_range
    # Indicadores customizados do usuário
    st.sidebar.subheader("Indicador Customizado")
    exp = st.sidebar.text_input("Digite expressão (ex: `df['A']/df['B']`)")
    if exp and st.sidebar.button("Adicionar indicador"):
        try:
            df["Custom"] = eval(exp)
            num_cols.append("Custom")
            st.success("Indicador adicionado!")
        except Exception as e:
            st.error(f"Erro: {e}")
    df_filtered = apply_filters(df, cat_filters, num_filters, date_col, date_range)

    # ========== Tabs do Dashboard ==========
    tab_kpi, tab_charts, tab_data, tab_manut, tab_geo, tab_rel = st.tabs([
        "🌟 KPIs", "📈 Gráficos", "📑 Dados", "🛠️ Manutenção", "🗺️ Mapa", "📤 Exportar/Compartilhar"
    ])

    # ===================== KPIs EM CARDS APENAS NA ABA KPIS =======================
    with tab_kpi:
        st.markdown("## Principais Indicadores")
        kpis = [
            {
                "titulo": "Eficiência de Motor (%)",
                "valor": df_filtered["Eficiência de Motor (%)"].mean() if "Eficiência de Motor (%)" in df_filtered else None,
                "cor": "#0074D9", "icone": "⚡", "meta": 65
            },
            {
                "titulo": "Área Operacional (ha)",
                "valor": df_filtered["Área Operacional (ha)"].sum() if "Área Operacional (ha)" in df_filtered else None,
                "cor": "#2ECC40", "icone": "🌱", "meta": None
            },
            {
                "titulo": "Consumo Médio (l/ha)",
                "valor": df_filtered["Consumo Médio (l/ha)"].mean() if "Consumo Médio (l/ha)" in df_filtered else None,
                "cor": "#B10DC9", "icone": "🛢️", "meta": None
            },
            {
                "titulo": "Rendimento Operacional (ha/h)",
                "valor": df_filtered["Rendimento Operacional (ha/h)"].mean() if "Rendimento Operacional (ha/h)" in df_filtered else None,
                "cor": "#FF851B", "icone": "🚜", "meta": None
            },
            {
                "titulo": "Velocidade Média Efetiva (km/h)",
                "valor": df_filtered["Velocidade Média Efetiva (km/h)"].mean() if "Velocidade Média Efetiva (km/h)" in df_filtered else None,
                "cor": "#39CCCC", "icone": "🏁", "meta": None
            },
            # ---------------------------------- Novos cards analíticos
            {
                "titulo": "Tempo Efetivo Médio (h)",
                "valor": df_filtered["Tempo Efetivo (h)"].mean() if "Tempo Efetivo (h)" in df_filtered else None,
                "cor": "#FFDC00", "icone": "⏱️", "meta": None
            },
            {
                "titulo": "Média de RPM em Efetivo",
                "valor": df_filtered["RPM Médio em Efetivo"].mean() if "RPM Médio em Efetivo" in df_filtered else None,
                "cor": "#85144b", "icone": "🔄", "meta": None
            },
            {
                "titulo": "Número de Operadores",
                "valor": df_filtered["Operador"].nunique() if "Operador" in df_filtered else None,
                "cor": "#7FDBFF", "icone": "👤", "meta": None
            },
            {
                "titulo": "Equipamentos Utilizados",
                "valor": df_filtered["Equipamento"].nunique() if "Equipamento" in df_filtered else None,
                "cor": "#3D9970", "icone": "🧰", "meta": None
            },
        ]
        cols = st.columns(len(kpis))
        for i, kpi in enumerate(kpis):
            valor = kpi["valor"]
            meta = kpi["meta"]
            delta = f"{valor-meta:.2f}" if meta and valor is not None else ""
            with cols[i]:
                if valor is not None:
                    st.markdown(
                        f"""
                        <div style="
                            background:{kpi['cor']};
                            border-radius:12px;
                            padding:18px 8px 14px 8px;
                            box-shadow:0 2px 8px #ddd;
                            text-align:center;
                        ">
                            <span style="font-size:36px;">{kpi['icone']}</span><br>
                            <span style="font-size:17px;font-weight:600">{kpi['titulo']}</span><br>
                            <span style="font-size:30px;font-weight:bold;line-height:1.2">{valor:.2f if isinstance(valor, float) else valor}</span>
                            {f"<br><span style='font-size:15px;'>Meta: {meta:.2f}</span>" if meta else ""}
                            {f"<br><span style='font-size:14px;color:#FFF;font-weight:400'>Δ {delta}</span>" if meta else ""}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""<div style="
                                background:#DDDDDD;
                                border-radius:12px;
                                padding:18px 8px 14px 8px;
                                text-align:center;">Dado não encontrado</div>""",
                        unsafe_allow_html=True
                    )

    # --------------- Gráficos (corrigido area_col e op_col) ----------------------
    with tab_charts:
        area_col = next((col for col in df_filtered.columns if "área operacional" in col.lower()), None)
        op_col = next((col for col in df_filtered.columns if "operador" in col.lower()), None)
        if area_col and op_col:
            area_bar = df_filtered.groupby(op_col)[area_col].sum().reset_index()
            fig = px.bar(
                area_bar, x=op_col, y=area_col, color=area_col,
                color_continuous_scale="Blues", text_auto=True,
                title="Área Operacional por Operador"
            )
            st.plotly_chart(fig, use_container_width=True)
        # ... adicione outros gráficos normalmente

    # ... demais tabs do dashboard seguem como antes
else:
    st.info("Faça o upload de uma planilha Excel para análise.")
