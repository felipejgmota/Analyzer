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
    if date_col and date_range and len(date_range) == 2:
        start, end = date_range
        end = pd.to_datetime(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtered = df_filtered[
            (df_filtered[date_col] >= pd.to_datetime(start)) &
            (df_filtered[date_col] <= end)
        ]
    for col, values in cat_filters.items():
        if values:
            df_filtered = df_filtered[df_filtered[col].isin(values)]
    for col, (min_v, max_v) in num_filters.items():
        df_filtered = df_filtered[(df_filtered[col] >= min_v) & (df_filtered[col] <= max_v)]
    return df_filtered

def export_pdf(df, title="Relatório Operacional"):
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
        min_date, max_date = df[date_col].min().date(), df[date_col].max().date()
        date_range = st.sidebar.date_input(
            "Selecione o intervalo de datas",
            [min_date, max_date],
            key="date_filter",
            format="DD-MM-YYYY"
        )
        if len(date_range) != 2:
            st.sidebar.warning("Selecione um intervalo de duas datas válidas.")

    cat_filters = {}
    for col in cat_cols:
        options = st.sidebar.multiselect(
            f"Filtrar {col}",
            options=sorted(df[col].dropna().unique()),
            default=sorted(df[col].dropna().unique()),
            key=f"catfilter_{col}"
        )
        cat_filters[col] = options

    num_filters = {}
    for col in num_cols:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        step = max((max_val-min_val)/1000, 0.01)
        selected_range = st.sidebar.slider(
            f"Intervalo {col}",
            min_val,
            max_val,
            (min_val, max_val),
            step=step,
            key=f"numfilter_{col}"
        )
        num_filters[col] = selected_range

    st.sidebar.subheader("Indicador Customizado")
    exp = st.sidebar.text_input("Digite expressão (ex: `df['A']/df['B']`)")
    if exp and st.sidebar.button("Adicionar indicador"):
        try:
            df["Custom"] = eval(exp)
            if "Custom" not in num_cols:
                num_cols.append("Custom")
            st.success("Indicador adicionado!")
        except Exception as e:
            st.error(f"Erro na expressão: {e}")

    df_filtered = apply_filters(df, cat_filters, num_filters, date_col, date_range)

    tab_kpi, tab_charts, tab_data, tab_manut, tab_geo, tab_sim, tab_rel = st.tabs([
        "🌟 KPIs", "📈 Gráficos", "📑 Dados", "🛠️ Manutenção", "🗺️ Mapa", "🧮 Simulador", "📤 Exportar"
    ])

    ######################## KPIs EM CARDS ########################
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
        kpi_options = {
            "Número de Talhões": ("Talhão", lambda d: d["Talhão"].nunique() if "Talhão" in d else None),
            "Consumo Médio Efetivo (l/h)": ("Consumo Médio Efetivo (l/h)", lambda d: d["Consumo Médio Efetivo (l/h)"].mean() if "Consumo Médio Efetivo (l/h)" in d else None),
            "Velocidade Média (km/h)": ("Velocidade Média Efetiva (km/h)", lambda d: d["Velocidade Média Efetiva (km/h)"].mean() if "Velocidade Média Efetiva (km/h)" in d else None),
            "RPM Médio": ("RPM Médio em Efetivo", lambda d: d["RPM Médio em Efetivo"].mean() if "RPM Médio em Efetivo" in d else None)
        }
        selected_extra_kpis = st.multiselect("Selecione KPIs adicionais para exibir", options=list(kpi_options.keys()))
        for kpi_name in selected_extra_kpis:
            title, func = kpi_options[kpi_name]
            val = func(df_filtered)
            kpis.append({
                "titulo": kpi_name,
                "valor": val,
                "cor": "#FF69B4",
                "icone": "📊",
                "meta": None
            })
        cols = st.columns(min(len(kpis), 4), gap="large")
        for i, kpi in enumerate(kpis):
            valor = kpi["valor"]
            meta = kpi["meta"]
            delta = f"{valor-meta:.2f}" if meta and valor is not None else ""
            valor_formatado = f"{valor:.2f}" if isinstance(valor, float) else str(valor) if valor is not None else "N/A"
            with cols[i % 4]:
                st.markdown(
                    f"""
                    <div style="
                        background:{kpi['cor']};
                        border-radius:12px;
                        padding:24px 12px;
                        box-shadow:0 3px 12px #ccc;
                        text-align:center;
                    ">
                        <div style="font-size:40px;line-height:1">{kpi['icone']}</div>
                        <div style="font-size:19px;font-weight:700;margin-top:6px">{kpi['titulo']}</div>
                        <div style="font-size:44px;font-weight:900;margin:6px 0 2px 0">{valor_formatado}</div>
                        {f"<div style='font-size:16px;font-weight:500;color:#eee'>Meta: {meta:.2f}</div>" if meta else ""}
                        {f"<div style='font-size:14px;color:#444;font-weight:600'>Δ {delta}</div>" if meta else ""}
                    </div>
                    """, unsafe_allow_html=True)

    ######################## DRILL-DOWN INTERATIVO ########################
    with tab_charts:
        st.markdown("## Análises Interativas e Drill-Down")
        op_col = next((col for col in df_filtered.columns if "operador" in col.lower()), None)
        area_col = next((col for col in df_filtered.columns if "área operacional" in col.lower()), None)
        if op_col and area_col:
            base_bar_df = df_filtered.groupby(op_col)[area_col].sum().reset_index()
            fig = px.bar(base_bar_df, x=op_col, y=area_col, text_auto=True, title="Área Operacional por Operador")
            st.plotly_chart(fig, use_container_width=True)
            operadores = base_bar_df[op_col].tolist()
            operador_select = st.selectbox("Clique em um operador para detalhar:", operadores)
            detalhados = df_filtered[df_filtered[op_col] == operador_select]
            st.markdown(f"### Detalhes do operador: {operador_select}")
            with st.expander("Tabela de Operações"):
                st.dataframe(detalhados.reset_index(drop=True))
            # KPIs detalhados do operador
            st.markdown("#### KPIs do Operador Selecionado")
            kpi_ef = detalhados["Eficiência de Motor (%)"].mean() if "Eficiência de Motor (%)" in detalhados else None
            kpi_ar = detalhados["Área Operacional (ha)"].sum() if "Área Operacional (ha)" in detalhados else None
            kpi_vel = detalhados["Velocidade Média Efetiva (km/h)"].mean() if "Velocidade Média Efetiva (km/h)" in detalhados else None
            st.metric("Eficiência de Motor (%)", f"{kpi_ef:.2f}" if kpi_ef is not None else "N/A")
            st.metric("Área Operacional (ha)", f"{kpi_ar:.2f}" if kpi_ar is not None else "N/A")
            st.metric("Velocidade Média Efetiva (km/h)", f"{kpi_vel:.2f}" if kpi_vel is not None else "N/A")

        # Outros gráficos múltiplos sugeridos
        ef_col = next((col for col in df_filtered.columns if "eficiência de motor" in col.lower()), None)
        consumo_col = next((col for col in df_filtered.columns if "consumo médio" in col.lower()), None)
        rend_col = next((col for col in df_filtered.columns if "rendimento operacional" in col.lower()), None)

        if ef_col and op_col:
            ef_bar = df_filtered.groupby(op_col)[ef_col].mean().reset_index().sort_values(by=ef_col, ascending=False)
            fig2 = px.bar(ef_bar, x=op_col, y=ef_col, color=ef_col, color_continuous_scale="Viridis", text_auto=".2f")
            st.plotly_chart(fig2, use_container_width=True)

        if consumo_col and op_col:
            cons_bar = df_filtered.groupby(op_col)[consumo_col].mean().reset_index()
            fig3 = px.box(df_filtered, x=op_col, y=consumo_col, points="all")
            st.plotly_chart(fig3, use_container_width=True)

        if rend_col and op_col:
            rend_scatter = df_filtered.groupby(op_col)[rend_col].mean().reset_index()
            fig4 = px.scatter(rend_scatter, x=op_col, y=rend_col, size=rend_col, color=rend_col, color_continuous_scale=px.colors.sequential.Plasma)
            st.plotly_chart(fig4, use_container_width=True)

        if num_cols:
            numeric_to_plot = st.selectbox("Selecione coluna para Histograma e Boxplot", num_cols, index=0)
            fig_hist = px.histogram(df_filtered, x=numeric_to_plot, marginal="box", nbins=25, title=f"Distribuição de {numeric_to_plot}")
            st.plotly_chart(fig_hist, use_container_width=True)

    ######################## Dados ########################
    with tab_data:
        st.markdown("## Dados filtrados")
        st.dataframe(df_filtered.reset_index(drop=True))

    ######################## Manutenção ########################
    with tab_manut:
        st.markdown("## Análise e alertas de Manutenção")
        manut_cols = [col for col in df_filtered.columns if 'manut' in col.lower()]
        horimetro_cols = [col for col in df_filtered.columns if 'horimet' in col.lower()]
        eq_col = next((c for c in df_filtered.columns if 'equipamento' in c.lower()), None)

        if manut_cols and horimetro_cols:
            hor_col = horimetro_cols[0]
            manut_col = manut_cols[0]
            limite_hor = st.number_input("Horímetro mínimo para alerta", min_value=0, value=1000)
            status_alerta = st.multiselect("Status de manutenção para alerta", ['sim', 'pendente', 'agendar'], default=['pendente', 'agendar'])
            alerta_df = df_filtered[
                (df_filtered[hor_col] >= limite_hor) &
                (df_filtered[manut_col].fillna('').astype(str).str.lower().isin([s.lower() for s in status_alerta]))
            ]
            if not alerta_df.empty:
                st.warning(f"{len(alerta_df)} alertas de manutenção detectados!")
                st.dataframe(alerta_df.reset_index(drop=True))
            else:
                st.success("Nenhum alerta de manutenção pendente encontrado.")

            manut_status = df_filtered[manut_col].value_counts().reset_index()
            if not manut_status.empty:
                fig_pie = px.pie(manut_status, names='index', values=manut_col, 
                                 title="Distribuição Status de Manutenção", color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Colunas para alertas de manutenção ou horímetro não encontradas.")

    ######################## Mapa ########################
    with tab_geo:
        st.markdown("## Mapa Interativo")
        lat_candidates = [col for col in df.columns if 'lat' in col.lower()]
        lon_candidates = [col for col in df.columns if 'lon' in col.lower() or 'long' in col.lower()]
        if lat_candidates and lon_candidates:
            lat_col = lat_candidates[0]
            lon_col = lon_candidates[0]
            map_data = df_filtered[[lat_col, lon_col]].dropna()
            if not map_data.empty:
                m = folium.Map(location=[map_data[lat_col].mean(), map_data[lon_col].mean()], zoom_start=12, tiles='OpenStreetMap')
                for _, row in map_data.iterrows():
                    folium.CircleMarker(
                        location=[row[lat_col], row[lon_col]],
                        radius=6,
                        color='#007AFF',
                        fill=True,
                        fill_opacity=0.8
                    ).add_to(m)
                st_folium(m, width=950, height=400)
            else:
                st.info("Não há dados geográficos disponíveis após filtro.")
        else:
            st.info("Colunas de latitude e longitude não encontradas no dataset.")

    ######################## Simulador e Cenários ########################
                        # ...código anterior de imports, utils, filtros, dados (mantenha igual)...

# INSIRA ESSE TRECHO NA ABA DE SIMULADOR/CENÁRIOS (substitua o bloco 'with tab_sim' anterior):

with tab_sim:
    st.markdown("## Simulador e Cenários 'E se?'")
    st.info("Os parâmetros reais abaixo foram calculados automaticamente a partir dos dados filtrados (faixa das últimas operações). Ajuste os sliders e compare.")

    # EXTRAIR PARÂMETROS REAIS DOS DADOS FILTRADOS
    def get_real(param_col, agg='mean'):
        if param_col in df_filtered:
            if agg == 'mean':
                return float(df_filtered[param_col].mean())
            elif agg == 'min':
                return float(df_filtered[param_col].min())
            elif agg == 'max':
                return float(df_filtered[param_col].max())
        return None

    velocidade_real = get_real("Velocidade Média Efetiva (km/h)")
    eficiencia_real = get_real("Eficiência de Motor (%)")
    consumo_real = get_real("Consumo Médio (l/ha)")
    area_real = get_real("Área Operacional (ha)", agg='sum')

    # Definir bounds reais automáticos
    vel_min, vel_max = get_real("Velocidade Média Efetiva (km/h)", 'min'), get_real("Velocidade Média Efetiva (km/h)", 'max')
    ef_min, ef_max = get_real("Eficiência de Motor (%)", 'min'), get_real("Eficiência de Motor (%)", 'max')
    cons_min, cons_max = get_real("Consumo Médio (l/ha)", 'min'), get_real("Consumo Médio (l/ha)", 'max')
    area_min, area_max = get_real("Área Operacional (ha)", 'min'), get_real("Área Operacional (ha)", 'max')

    # SIMULADOR COM SLIDERS USANDO FAIXA REAL DO BANCO DE DADOS
    velocidade_sim = st.slider(
        "Velocidade Média Simulada (km/h)",
        min_value=float(vel_min or 5),
        max_value=float(vel_max or 40),
        value=float(velocidade_real or 15),
        step=0.1
    )
    eficiencia_sim = st.slider(
        "Eficiência de Motor Simulada (%)",
        min_value=float(ef_min or 30),
        max_value=float(ef_max or 100),
        value=float(eficiencia_real or 65),
        step=0.1
    )
    consumo_sim = st.slider(
        "Consumo Médio Simulado (l/ha)",
        min_value=float(cons_min or 0.5),
        max_value=float(cons_max or 10),
        value=float(consumo_real or 2.0),
        step=0.01
    )
    area_op_sim = st.slider(
        "Área Operacional Simulada (ha)",
        min_value=float(area_min or 100),
        max_value=float(area_max or 5000),
        value=float(area_real or 1000),
        step=10.0
    )

    # TABELA COMPARATIVA DOS PARÂMETROS REAIS E SIMULADOS
    st.markdown("### Comparativo: Real vs. Simulado")
    comparativo = pd.DataFrame({
        "Parâmetro": ["Velocidade Média (km/h)", "Eficiência de Motor (%)", "Consumo Médio (l/ha)", "Área Operacional (ha)"],
        "Valor Real": [velocidade_real, eficiencia_real, consumo_real, area_real],
        "Simulado": [velocidade_sim, eficiencia_sim, consumo_sim, area_op_sim],
        "Delta": [
            velocidade_sim-(velocidade_real if velocidade_real else 0),
            eficiencia_sim-(eficiencia_real if eficiencia_real else 0),
            consumo_sim-(consumo_real if consumo_real else 0),
            area_op_sim-(area_real if area_real else 0)
        ]
    })
    st.dataframe(comparativo)

    # FEEDBACK AUTOMÁTICO
    st.markdown("### Feedback e Recomendações")
    def feedback(param, delta, nome, unidade, meta=None):
        if meta is not None:
            if param >= meta:
                st.success(f"{nome}: *{param:.2f} {unidade}* está acima da meta ({meta:.2f}). Ótimo desempenho!")
            else:
                st.warning(f"{nome}: *{param:.2f} {unidade}* está abaixo da meta ({meta:.2f}). Considere ajustes.")
        else:
            if delta > 0:
                st.info(f"{nome} aumentou em relação à referência real (+{delta:.2f} {unidade})")
            elif delta < 0:
                st.info(f"{nome} reduziu em relação à referência real ({delta:.2f} {unidade})")
            else:
                st.info(f"{nome} igual ao da referência real.")

    if velocidade_real is not None:
        feedback(velocidade_sim, velocidade_sim-velocidade_real, "Velocidade Média", "km/h")
    if eficiencia_real is not None:
        feedback(eficiencia_sim, eficiencia_sim-eficiencia_real, "Eficiência de Motor (%)", "%", meta=65)
    if consumo_real is not None:
        feedback(consumo_sim, consumo_sim-consumo_real, "Consumo Médio", "l/ha")
    if area_real is not None:
        feedback(area_op_sim, area_op_sim-area_real, "Área Operacional", "ha")

    if consumo_real is not None:
        potencial_economia = (consumo_real-consumo_sim)*area_op_sim
        if potencial_economia > 0:
            st.success(f"Potencial economia de insumos: {potencial_economia:.2f} litros por operação simulada.")
        elif potencial_economia < 0:
            st.warning(f"Simulação indica *aumento* de consumo em {abs(potencial_economia):.2f} litros.")

    st.caption("Valores reais baseados em médias e extremos dos dados filtrados. Ajuste os sliders para comparar e avaliar impacto dos cenários.")


    ######################## Exportar ########################
    with tab_rel:
        st.markdown("## Exportar/Compartilhar")
        st.download_button(
            "Baixar CSV dos dados filtrados",
            data=df_filtered.to_csv(index=False).encode('utf-8'),
            file_name="dados_filtrados.csv",
            mime="text/csv"
        )
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df_filtered.to_excel(writer)
        st.download_button(
            "Baixar Excel dos dados filtrados",
            data=excel_buffer.getvalue(),
            file_name="dados_filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        try:
            pdf_data = export_pdf(df_filtered).getvalue()
            st.download_button(
                "Baixar PDF dos dados filtrados",
                data=pdf_data,
                file_name="dados_filtrados.pdf",
                mime="application/pdf"
            )
        except Exception:
            st.info("PDF export requer a biblioteca 'reportlab' instalada no ambiente.")

else:
    st.info("Faça o upload de uma planilha Excel para análise.")

