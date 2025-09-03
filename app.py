import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import io

# PAGE CONFIG
st.set_page_config(layout="wide", page_title="Dashboard Operacional Avançado", initial_sidebar_state="expanded")

st.title("📊 Dashboard de Análise Operacional Avançado")

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

    # ========== KPIs e Simulação de Meta ==========
    with tab_kpi:
        st.markdown("### KPIs Customizados com Meta")
        eficiencia_col = next((col for col in df_filtered.columns if "efici" in col.lower()), None)
        area_col = next((col for col in df_filtered.columns if "área" in col.lower()), None)
        velocidade_col = next((col for col in df_filtered.columns if "veloc" in col.lower()), None)
        consumo_col = next((col for col in df_filtered.columns if "consumo" in col.lower()), None)

        meta_efi = st.number_input("Meta de Eficiência (%)", min_value=0., value=65.)
        cols = st.columns(4)
        if eficiencia_col: 
            with cols[0]:
                val = df_filtered[eficiencia_col].mean()
                delta = val-meta_efi
                st.metric("Eficiência (%)", f"{val:.2f}", f"{delta:+.2f} vs meta")
        if area_col: 
            with cols[1]:
                st.metric("Área Operacional (ha)", f"{df_filtered[area_col].sum():.1f}")
        if velocidade_col:
            with cols[2]:
                st.metric("Velocidade Média (km/h)", f"{df_filtered[velocidade_col].mean():.2f}")
        if consumo_col:
            with cols[3]:
                st.metric("Consumo Médio (l/ha)", f"{df_filtered[consumo_col].mean():.2f}")

        # Simulação de Cenário
        st.markdown("#### Simulação: ajuste de velocidade")
        sim_vel = st.slider("Velocidade simulada (km/h)", min_value=5., max_value=30., value=float(df_filtered[velocidade_col].mean()) if velocidade_col else 15.)
        if velocidade_col:
            df_sim = df_filtered.copy()
            df_sim[velocidade_col] = sim_vel
            st.write(f"Nova média: {df_sim[velocidade_col].mean():.2f} km/h")

    # ========== Gráficos Profissionais ==========
    with tab_charts:
        st.markdown("### Gráficos & Tendências")
        if area_col and "Operador" in df_filtered.columns:
            op_col = "Operador"
            area_bar = df_filtered.groupby(op_col)[area_col].sum().reset_index()
            fig = px.bar(area_bar, x=op_col, y=area_col, color=area_col,
                        color_continuous_scale="Blues", text_auto=True, title="Área Operacional por Operador")
            st.plotly_chart(fig, use_container_width=True)
        if velocidade_col:
            fig2 = px.line(df_filtered, x=date_col if date_col else None, y=velocidade_col, markers=True,
                        title="Velocidade Média ao longo do tempo")
            st.plotly_chart(fig2, use_container_width=True)
        if num_cols:
            col_graf = st.selectbox("Selecione coluna numérica para Histograma/Boxplot", num_cols)
            fig_hist = px.histogram(df_filtered, x=col_graf, marginal="box", nbins=30, title=f"Distribuição de {col_graf}")
            st.plotly_chart(fig_hist, use_container_width=True)

    # ========== Tabela, Download, Histórico ==========
    with tab_data:
        st.markdown("### Dados Filtrados")
        st.dataframe(df_filtered)
        st.download_button("Baixar dados filtrados CSV", data=df_filtered.to_csv(index=False), file_name="filtrado.csv")
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_filtered.to_excel(writer)
        st.download_button("Baixar Excel", data=excel_buffer.getvalue(), file_name="filtrado.xlsx")

    # ========== Manutenção & Alertas Automáticos ==========
    with tab_manut:
        st.markdown("### Alertas e Relatórios de Manutenção")
        manut_cols = [col for col in df_filtered.columns if 'manut' in col.lower()]
        horimetro_cols = [col for col in df_filtered.columns if 'horimet' in col.lower()]
        eq_col = next((c for c in df_filtered.columns if 'equipamento' in c.lower()), None)
        if manut_cols and horimetro_cols:
            hor_col = horimetro_cols[0]
            manut_col = manut_cols[0]
            limite_hor = st.slider("Horímetro mínimo alerta", min_value=0, value=1000)
            status_alerta = st.multiselect("Status alerta", ['sim','pendente','agendar'], default=['pendente','agendar'])
            alerta_df = df_filtered[(df_filtered[hor_col]>=limite_hor)&(df_filtered[manut_col].astype(str).str.lower().isin([s.lower() for s in status_alerta]))]
            if not alerta_df.empty:
                st.warning(f"{len(alerta_df)} alertas de manutenção detectados!")
                st.dataframe(alerta_df)
        # Pizza
        if manut_cols:
            df_pizza = df_filtered[manut_cols[0]].value_counts().reset_index()
            st.plotly_chart(px.pie(df_pizza, names="index", values=manut_cols[0], title="Status de Manutenção"), use_container_width=True)

    # ========== Geospacial/Mapa ==========
    with tab_geo:
        lat_candidates = [col for col in df.columns if 'lat' in col.lower()]
        lon_candidates = [col for col in df.columns if 'lon' in col.lower() or 'long' in col.lower()]
        if lat_candidates and lon_candidates:
            lat_col = lat_candidates[0]
            lon_col = lon_candidates[0]
            map_data = df_filtered[[lat_col, lon_col]].dropna()
            st.markdown("#### Equipamentos Georreferenciados")
            if not map_data.empty:
                m = folium.Map(location=[map_data[lat_col].mean(), map_data[lon_col].mean()], zoom_start=12, tiles='OpenStreetMap')
                for _, row in map_data.iterrows():
                    folium.CircleMarker(location=[row[lat_col], row[lon_col]], radius=6, color='#007AFF', fill=True, fill_opacity=0.8).add_to(m)
                st_folium(m, width=950, height=400)
        else:
            st.info("Colunas de local geográfico não encontradas.")

    # ========== Exportação PDF/Compartilhamento ==========
    with tab_rel:
        st.markdown("### Compartilhar Relatórios")
        st.download_button(
            "Baixar PDF do relatório filtrado",
            data=export_pdf(df_filtered).getvalue(),
            file_name="relatorio_operacional.pdf"
        )
        st.write("**Compartilhamento:** Este recurso pode ser ampliado para integração por e-mail, WhatsApp, APIs externas...")

    # ========== Feedback/Tutorial ==========
    st.sidebar.subheader("Feedback e Dúvidas")
    fb = st.sidebar.text_area("Envie sua sugestão ou dúvida:")
    if st.sidebar.button("Enviar Feedback"):
        st.success("Obrigado! Sua sugestão foi registrada.")
    if st.sidebar.button("Abrir tutorial rápido"):
        st.sidebar.info("1. Carregue um arquivo Excel\n2. Ajuste filtros\n3. Navegue entre tabs para KPIs, gráficos, manutenção e mapas.\n4. Baixe os dados ou relatórios.\n5. Veja exemplos na documentação.")

else:
    st.info("Faça o upload de uma planilha Excel para análise.")

