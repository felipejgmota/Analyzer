import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# ========== Configuração da Página ==========
st.set_page_config(layout="wide", page_title="Dashboard Operacional Moderno")

st.markdown("<style>h1 {margin-bottom: 0px;} </style>", unsafe_allow_html=True)
st.title("📊 Dashboard de Análise Operacional")

# ========== Funções Utilitárias ==========
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

# ========== Upload e Seleção ==========
uploaded_file = st.file_uploader("Selecione uma planilha Excel...", type=["xlsx"])

if uploaded_file is not None:
    all_sheets = load_excel(uploaded_file)
    sheet_names = list(all_sheets.keys())
    sheet_selected = st.selectbox("Selecione a aba da planilha para análise", sheet_names)
    df = preprocess_df(all_sheets[sheet_selected])
    cat_cols = df.select_dtypes(include='object').columns.tolist()
    num_cols = df.select_dtypes(include='number').columns.tolist()
    date_cols = df.select_dtypes(include='datetime').columns.tolist()

    # ========== Filtros na Sidebar ==========
    st.sidebar.header("Filtros")
    date_col, date_range = None, None
    if date_cols:
        date_col = st.sidebar.selectbox("Coluna de data para filtro", date_cols)
        min_date, max_date = df[date_col].min(), df[date_col].max()
        date_range = st.sidebar.date_input("Selecione o intervalo de datas", [min_date, max_date])
    cat_filters = {}
    for col in cat_cols:
        options = st.sidebar.multiselect(f"Filtrar {col}", options=df[col].dropna().unique(), default=df[col].dropna().unique())
        cat_filters[col] = options
    num_filters = {}
    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.sidebar.slider(f"Intervalo {col}", min_val, max_val, (min_val, max_val))
        num_filters[col] = selected_range

    df_filtered = apply_filters(df, cat_filters, num_filters, date_col, date_range)

    # ========== Seções em Tabs ==========
    tab_kpi, tab_charts, tab_data, tab_manut = st.tabs(
        ["🌟 KPIs", "📈 Gráficos", "📑 Dados", "🛠️ Manutenção"]
    )

    # ========== KPIs em Cards Coloridos ==========
    with tab_kpi:
        st.markdown("### Principais KPIs")
        # Exemplo dinâmico de KPIs, altere nomes conforme planilha
        kpis = {
            "Eficiência de Motor (%)": ("Eficiência de Motor (%)", 65, "green", "⚡"),
            "Área Operacional (ha)": ("Área Operacional (ha)", None, "blue", "🌱"),
            "Consumo Médio (l/ha)": ("Consumo Médio (l/ha)", None, "purple", "🛢️"),
            "Rendimento Operacional (ha/h)": ("Rendimento Operacional (ha/h)", None, "orange", "🚜"),
            "Velocidade Média Efetiva (km/h)": ("Velocidade Média Efetiva (km/h)", None, "teal", "🏁"),
        }
        kpi_cols = st.columns(len(kpis))
        for i, (label, (col_name, meta, cor, icon)) in enumerate(kpis.items()):
            if col_name in df_filtered.columns:
                valor = df_filtered[col_name].mean()
                delta = None
                if meta is not None:
                    delta = valor - meta
                with kpi_cols[i]:
                    st.markdown(
                        f"""
                        <div style="border-radius:12px;padding:18px 8px 14px 8px;background:{cor};color:white;box-shadow:0 2px 8px #ddd;text-align:center;">
                            <span style="font-size:36px;">{icon}</span><br>
                            <span style="font-size:17px;font-weight:600">{label}</span><br>
                            <span style="font-size:38px;font-weight:bold;line-height:1.2">{valor:.2f}</span>
                            <br>{f"<span style='font-size:15px;font-weight:400'>Meta: {meta:.2f}</span>" if meta else ""}
                            {f"<br><span style='font-size:14px;color:#FFF;font-weight:400'>Δ {delta:.2f}</span>" if delta is not None else ""}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        st.markdown("")

    # ========== Gráficos Power BI-Like ==========
    with tab_charts:
        st.markdown("### Gráficos Interativos")
        # Gráfico 1: Área Operacional por Operador
        op_col = None
        for c in df_filtered.columns:
            if 'operador' in c.lower():
                op_col = c
        area_col = None
        for c in df_filtered.columns:
            if 'área operacional' in c.lower():
                area_col = c
        if op_col and area_col:
            df_bar = df_filtered.groupby(op_col)[area_col].sum().reset_index()
            fig_bar = px.bar(
                df_bar,
                x=op_col,
                y=area_col,
                color=area_col,
                color_continuous_scale="Blues",
                text_auto=True,
                title="Área Operacional por Operador"
            )
            fig_bar.update_layout(
                plot_bgcolor='#fff',
                paper_bgcolor='#fff',
                font=dict(size=16),
                title_font=dict(size=24, color="navy")
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        # Gráfico 2: Eficiência de Motor por Equipamento
        eq_col = None
        for c in df_filtered.columns:
            if 'equipamento' in c.lower():
                eq_col = c
        ef_col = None
        for c in df_filtered.columns:
            if 'eficiência de motor' in c.lower():
                ef_col = c
        if eq_col and ef_col:
            df_bar2 = df_filtered.groupby(eq_col)[ef_col].mean().reset_index()
            fig_bar2 = px.bar(
                df_bar2,
                x=eq_col,
                y=ef_col,
                color=ef_col,
                text_auto=True,
                title="Eficiência de Motor (%) por Equipamento",
                color_continuous_scale="Viridis"
            )
            fig_bar2.update_layout(plot_bgcolor='#f8f9fa', paper_bgcolor='#f8f9fa')
            st.plotly_chart(fig_bar2, use_container_width=True)
        # Gráfico Selecionável
        if num_cols:
            col_graf = st.selectbox("Selecione coluna numérica para Histograma/Boxplot", num_cols)
            fig_hist = px.histogram(df_filtered, x=col_graf, marginal="box", nbins=30, title=f"Distribuição de {col_graf}")
            fig_hist.update_layout(plot_bgcolor='#fff')
            st.plotly_chart(fig_hist, use_container_width=True)

    # ========== Dados em Tabela ==========
    with tab_data:
        st.markdown("### Dados após filtros")
        st.dataframe(df_filtered)
        st.download_button(
            label="Baixar dados filtrados",
            data=df_filtered.to_csv(index=False).encode('utf-8'),
            file_name=f"dados_filtrados_{sheet_selected}.csv",
            mime="text/csv"
        )

    # ========== Manutenção Gráfica (Cards + Pizza) ==========
    with tab_manut:
        manut_cols = [col for col in df_filtered.columns if 'manut' in col.lower()]
        horimetro_cols = [col for col in df_filtered.columns if 'horimet' in col.lower()]
        eq_col = None
        for c in df_filtered.columns:
            if 'equipamento' in c.lower():
                eq_col = c
        st.markdown("### Alertas e Custos de Manutenção")
        if manut_cols and horimetro_cols:
            horimetro_col = horimetro_cols[0]
            manut_col = manut_cols[0]
            limite_horimetro = st.sidebar.number_input("Horímetro mínimo para alerta", min_value=0, value=1000)
            status_alerta = st.sidebar.multiselect("Status de manutenção para alerta", ['sim', 'pendente', 'agendar'], default=['pendente', 'agendar'])
            alerta_df = df_filtered[
                (df_filtered[horimetro_col] >= limite_horimetro)
                & (df_filtered[manut_col].fillna('').astype(str).str.lower().isin([s.lower() for s in status_alerta]))
            ]
            if not alerta_df.empty:
                st.warning(f"{len(alerta_df)} equipamentos com ALERTA de manutenção.")
                st.dataframe(alerta_df[[horimetro_col, manut_col] + cat_cols])
            else:
                st.success("Nenhum alerta de manutenção pendente encontrado.")
            # Exemplo de pizza de status de manutenção
            manut_status = df_filtered[manut_col].value_counts().reset_index()
            fig_pizza = px.pie(manut_status, names='index', values=manut_col, title="Distribuição Status Manutenção", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Colunas para alertas de manutenção ou horímetro não encontradas.")

    # ========== Mapa Interativo ==========
    st.markdown("### Mapa Interativo")
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
                    color='#3498db',
                    fill=True,
                    fill_opacity=0.7
                ).add_to(m)
            st_folium(m, width=950, height=400)
        else:
            st.info("Não há dados geográficos disponíveis após filtro.")
    else:
        st.info("Colunas para latitude e longitude não encontradas no dataset.")
else:
    st.info("Faça o upload de uma planilha Excel para análise.")
