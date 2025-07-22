import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
# Assegure-se de que 'column_mapping.py' esteja na mesma pasta
from column_mapping import column_mapping

# Helper function for Brazilian currency formatting (dot for thousands, comma for decimals)
def format_currency_br(value):
    if pd.isna(value) or value is None:
        return "R$ 0,00"
    # Format number with comma as decimal and dot as thousands, then swap them
    s_value = "{:,.2f}".format(value) # e.g., "1,234,567.89" (US locale default)
    # The trick: replace comma (US thousands) with a temp char, dot (US decimal) with comma, then temp char with dot
    s_value = s_value.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s_value}"

# Helper function for Brazilian integer formatting (dot for thousands, no decimals)
def format_integer_br(value):
    if pd.isna(value) or value is None:
        return "0"
    # Ensure value is treated as an integer before formatting
    int_value = int(value)
    s_value = "{:,.0f}".format(int_value) # e.g., "1,000" (US locale default)
    # The trick: replace comma (US thousands) with a temp char, dot (US decimal) with comma, then temp char with dot
    s_value = s_value.replace(",", "X").replace(".", ",").replace("X", ".")
    return s_value

# Configuração da página
st.set_page_config(
    page_title="Dashboard TopCity", 
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Verificação de senha OTIMIZADA
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    senha_correta = st.secrets["app_password"]
    with st.container():
        st.markdown("### 🔐 Acesso Restrito")
        senha = st.text_input("Digite a senha para acessar o dashboard:", type="password")
        if senha == senha_correta:
            st.session_state.autenticado = True
            st.success("✅ Acesso liberado com sucesso!")
            st.rerun()
        elif senha != "":
            st.error("❌ Senha incorreta. Tente novamente.")
    st.stop() 

# CSS personalizado REDUZIDO
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #96ca00 0%, #4e9f00 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        font-size: 1.1em;
        margin-bottom: 0.5rem;
        opacity: 0.8;
    }
    .metric-value {
        font-size: 2.2em;
        font-weight: bold;
    }
    .main-header {
        background: linear-gradient(90deg, #96ca00 0%, #4e9f00  100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    div.stButton > button {
        background-color: #96ca00;
        color: white;
        border-radius: 5px;
        border: 1px solid #96ca00;
        padding: 0.5em 1em;
    }
    div.stButton > button:hover {
        background-color: #6b8f00;
        color: white;
        border: 1px solid #6b8f00;
    }
</style>
""", unsafe_allow_html=True)

# Título Principal do Dashboard
st.markdown("<h1 class='main-header'>Dashboard de Análise de Produtos e Cidades 🏙️</h1>", unsafe_allow_html=True)

# FUNÇÃO DE CARREGAMENTO OTIMIZADA
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_data():
    """
    Carrega e pré-processa os dados da planilha do Google Sheets.
    """
    sheet_id = '14Y-V3ezwo3LsHWERhSyURCtkQdN3drzv9F5JNRQnXEc'
    tab_name = 'Produtos_Cidades_Completas'
    google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab_name}"

    try:
        # Otimização: Especificar tipos de dados para acelerar o carregamento
        dtype_dict = {
            'faturamento': 'str',
            'faturamento_total_cidade_mes': 'str',
            'unidades_fisicas': 'float64',
            'pedidos': 'float64',
            'total_pedidos_cidade_mes': 'float64'
        }
        
        df = pd.read_csv(google_sheet_url, dtype=dtype_dict)
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

    if df.empty:
        st.warning("A planilha está vazia.")
        st.stop()

    # PROCESSAMENTO OTIMIZADO
    with st.spinner("Processando dados..."):
        # Conversão de data otimizada
        df['mes'] = pd.to_datetime(df['mes'], format='%Y-%m', errors='coerce')
        
        # Conversão numérica otimizada usando vectorização
        numeric_columns = ['faturamento', 'faturamento_total_cidade_mes']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Preencher NaN com 0 para colunas numéricas
        numeric_cols = ['unidades_fisicas', 'pedidos', 'total_pedidos_cidade_mes']
        df[numeric_cols] = df[numeric_cols].fillna(0)

        # Renomear colunas
        df = df.rename(columns=column_mapping)

        # Calcular métricas derivadas usando operações vetorizadas
        df['Participação Faturamento Cidade Mês (%)'] = np.where(
            df['Faturamento Total da Cidade no Mês'] > 0,
            (df['Faturamento do Produto'] / df['Faturamento Total da Cidade no Mês']) * 100,
            0
        )

        df['Participação Pedidos Cidade Mês (%)'] = np.where(
            df['Total de Pedidos da Cidade no Mês'] > 0,
            (df['Pedidos com Produto'] / df['Total de Pedidos da Cidade no Mês']) * 100,
            0
        )

        df['Ticket Médio do Produto'] = np.where(
            df['Pedidos com Produto'] > 0,
            df['Faturamento do Produto'] / df['Pedidos com Produto'],
            0
        )
    
    return df

# Carregamento com indicador de progresso
with st.spinner("Carregando dados do Google Sheets..."):
    df = load_data()

# OTIMIZAÇÃO: Usar session_state para manter listas de opções
if 'filter_options' not in st.session_state:
    st.session_state.filter_options = {
        'months': sorted(df['Mês'].dt.to_period('M').unique().to_timestamp().tolist()),
        'estados': sorted(df['Estado'].unique().tolist()),
        'cidades': sorted(df['Cidade'].unique().tolist()),
        'produtos': sorted(df['Produto'].unique().tolist())
    }

# --- Sidebar para Filtros OTIMIZADA ---
st.sidebar.header("⚙️ Filtros Globais")

# Botão de resetar otimizado
if st.sidebar.button("🔄 Resetar Filtros"):
    keys_to_reset = ['selected_months', 'selected_estados', 'selected_cidades', 'selected_produtos']
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# Filtros com valores padrão otimizados
available_months = st.session_state.filter_options['months']
selected_months = st.sidebar.multiselect(
    "Selecione o(s) Mês(es)",
    options=available_months,
    default=st.session_state.get('selected_months', available_months[-3:]),  # Últimos 3 meses por padrão
    format_func=lambda x: x.strftime('%Y-%m'),
    key='month_filter'
)

selected_estados = st.sidebar.multiselect(
    "Selecione o(s) Estado(s)",
    options=st.session_state.filter_options['estados'],
    default=st.session_state.get('selected_estados', st.session_state.filter_options['estados'][:5]),  # Primeiros 5 estados
    key='estado_filter'
)

# Filtro de cidade otimizado
if selected_estados:
    available_cidades = sorted(df[df['Estado'].isin(selected_estados)]['Cidade'].unique())
else:
    available_cidades = st.session_state.filter_options['cidades']

selected_cidades = st.sidebar.multiselect(
    "Selecione a(s) Cidade(s)",
    options=available_cidades,
    default=st.session_state.get('selected_cidades', available_cidades[:10]),  # Primeiras 10 cidades
    key='cidade_filter'
)

selected_produtos = st.sidebar.multiselect(
    "Selecione o(s) Produto(s)",
    options=st.session_state.filter_options['produtos'],
    default=st.session_state.get('selected_produtos', []),
    key='produto_filter'
)

# APLICAÇÃO DE FILTROS OTIMIZADA
df_filtrado = df.copy()

# Aplicar filtros em sequência para reduzir o tamanho do DataFrame
if selected_months:
    df_filtrado = df_filtrado[df_filtrado['Mês'].isin(selected_months)]

if selected_estados:
    df_filtrado = df_filtrado[df_filtrado['Estado'].isin(selected_estados)]

if selected_cidades:
    df_filtrado = df_filtrado[df_filtrado['Cidade'].isin(selected_cidades)]

if selected_produtos:
    df_filtrado = df_filtrado[df_filtrado['Produto'].isin(selected_produtos)]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado. Ajuste os filtros.")
    st.stop()

# CÁLCULO DE KPIS OTIMIZADO
st.header("📊 Principais Indicadores")

@st.cache_data
def calculate_kpis(df_filtered, has_products_selected):
    if has_products_selected:
        total_faturamento = df_filtered['Faturamento do Produto'].sum()
        total_pedidos_kpi = df_filtered['Pedidos com Produto'].sum()
    else:
        # Usar groupby mais eficiente
        df_kpi = df_filtered.drop_duplicates(['Mês', 'Cidade'])[['Mês', 'Cidade', 'Total de Pedidos da Cidade no Mês', 'Faturamento Total da Cidade no Mês']]
        total_faturamento = df_kpi['Faturamento Total da Cidade no Mês'].sum()
        total_pedidos_kpi = df_kpi['Total de Pedidos da Cidade no Mês'].sum()

    total_unidades_fisicas = df_filtered['Unidades Compradas'].sum()
    ticket_medio_geral = total_faturamento / total_pedidos_kpi if total_pedidos_kpi > 0 else 0
    media_participacao_faturamento = df_filtered['Participação Faturamento Cidade Mês (%)'].mean()
    
    return total_faturamento, total_pedidos_kpi, total_unidades_fisicas, ticket_medio_geral, media_participacao_faturamento

# Calcular KPIs
kpis = calculate_kpis(df_filtrado, bool(selected_produtos))
total_faturamento, total_pedidos_kpi, total_unidades_fisicas, ticket_medio_geral, media_participacao_faturamento = kpis

# Display KPIs
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Faturamento Total</div>
        <div class="metric-value">{format_currency_br(total_faturamento)}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Total Pedidos</div>
        <div class="metric-value">{format_integer_br(total_pedidos_kpi)}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Unidades Compradas</div>
        <div class="metric-value">{format_integer_br(total_unidades_fisicas)}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Ticket Médio Geral</div>
        <div class="metric-value">{format_currency_br(ticket_medio_geral)}</div>
    </div>
    """, unsafe_allow_html=True)
with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">% Partic. Faturamento Prod. (Méd.)</div>
        <div class="metric-value">{media_participacao_faturamento:,.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ANÁLISE DE DESEMPENHO OTIMIZADA
st.header("📈 Análise de Desempenho")

@st.cache_data
def get_top_data(df_filtered, group_by, metric, n_items):
    """Função otimizada para calcular top N de qualquer métrica"""
    return df_filtered.groupby(group_by)[metric].sum().astype(float).nlargest(n_items).reset_index()

tab_produtos, tab_cidades, tab_estados = st.tabs(["Top Produtos", "Top Cidades", "Top Estados"])

with tab_produtos:
    st.subheader("Top Produtos por Métrica")
    metric_produto = st.selectbox(
        "Selecionar Métrica:",
        options=["Faturamento do Produto", "Unidades Compradas"],
        key='metric_produto_tab'
    )
    n_produtos = st.slider("Número de Produtos:", min_value=5, max_value=20, value=10, key='n_produtos_tab')

    top_produtos = get_top_data(df_filtrado, 'Produto', metric_produto, n_produtos)
    top_produtos.columns = ['Produto', 'Total']

    # Gráfico otimizado
    fig_top_produtos = px.bar(
        top_produtos,
        x='Total',
        y='Produto',
        orientation='h',
        title=f"Top {n_produtos} Produtos por {metric_produto}",
        color='Total',
        color_continuous_scale='Plasma'
    )
    
    fig_top_produtos.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )
    
    if metric_produto == "Faturamento do Produto":
        fig_top_produtos.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
    
    st.plotly_chart(fig_top_produtos, use_container_width=True)

with tab_cidades:
    st.subheader("Top Cidades por Métrica")
    metric_cidade = st.selectbox(
        "Selecionar Métrica:",
        options=["Faturamento do Produto", "Unidades Compradas", "Pedidos com Produto"],
        key='metric_cidade_tab'
    )
    n_cidades = st.slider("Número de Cidades:", min_value=5, max_value=20, value=10, key='n_cidades_tab')

    top_cidades = get_top_data(df_filtrado, 'Cidade', metric_cidade, n_cidades)
    top_cidades.columns = ['Cidade', 'Total']

    fig_top_cidades = px.bar(
        top_cidades,
        x='Total',
        y='Cidade',
        orientation='h',
        title=f"Top {n_cidades} Cidades por {metric_cidade}",
        color='Total',
        color_continuous_scale='Viridis'
    )
    
    fig_top_cidades.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )
    
    st.plotly_chart(fig_top_cidades, use_container_width=True)

with tab_estados:
    st.subheader("Top Estados por Métrica")
    metric_estado = st.selectbox(
        "Selecionar Métrica:",
        options=["Faturamento do Produto", "Unidades Compradas", "Pedidos com Produto"],
        key='metric_estado_tab'
    )
    n_estados = st.slider("Número de Estados:", min_value=5, max_value=15, value=10, key='n_estados_tab')

    top_estados = get_top_data(df_filtrado, 'Estado', metric_estado, n_estados)
    top_estados.columns = ['Estado', 'Total']

    fig_top_estados = px.bar(
        top_estados,
        x='Total',
        y='Estado',
        orientation='h',
        title=f"Top {n_estados} Estados por {metric_estado}",
        color='Total',
        color_continuous_scale='Cividis'
    )
    
    fig_top_estados.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )
    
    st.plotly_chart(fig_top_estados, use_container_width=True)

st.markdown("---")

# COMPARATIVOS OTIMIZADOS
st.header("🔄 Comparativos de Período")

if selected_months and len(selected_months) > 0:
    @st.cache_data
    def calculate_comparisons(df_base, selected_months, selected_cidades, selected_estados, selected_produtos):
        # Aplicar filtros base
        df_comp = df_base.copy()
        if selected_cidades:
            df_comp = df_comp[df_comp['Cidade'].isin(selected_cidades)]
        if selected_estados:
            df_comp = df_comp[df_comp['Estado'].isin(selected_estados)]
        
        min_month = min(selected_months)
        max_month = max(selected_months)
        
        # Período atual
        current_period = df_comp[
            (df_comp['Mês'] >= min_month) & (df_comp['Mês'] <= max_month)
        ]
        
        # Período anterior
        previous_month_start = min_month - pd.DateOffset(months=1)
        previous_month_end = min_month - pd.DateOffset(days=1)
        previous_period = df_comp[
            (df_comp['Mês'] >= previous_month_start) & (df_comp['Mês'] <= previous_month_end)
        ]
        
        if selected_produtos:
            current_period = current_period[current_period['Produto'].isin(selected_produtos)]
            previous_period = previous_period[previous_period['Produto'].isin(selected_produtos)]
            
            current_fat = current_period['Faturamento do Produto'].sum()
            current_ped = current_period['Pedidos com Produto'].sum()
            prev_fat = previous_period['Faturamento do Produto'].sum()
            prev_ped = previous_period['Pedidos com Produto'].sum()
        else:
            current_unique = current_period.drop_duplicates(['Mês', 'Cidade'])
            prev_unique = previous_period.drop_duplicates(['Mês', 'Cidade'])
            
            current_fat = current_unique['Faturamento Total da Cidade no Mês'].sum()
            current_ped = current_unique['Total de Pedidos da Cidade no Mês'].sum()
            prev_fat = prev_unique['Faturamento Total da Cidade no Mês'].sum()
            prev_ped = prev_unique['Total de Pedidos da Cidade no Mês'].sum()
        
        return current_fat, current_ped, prev_fat, prev_ped
    
    current_fat, current_ped, prev_fat, prev_ped = calculate_comparisons(
        df, selected_months, selected_cidades, selected_estados, selected_produtos
    )
    
    # Calcular variações
    fat_diff = current_fat - prev_fat
    fat_perc = (fat_diff / prev_fat * 100) if prev_fat > 0 else 0
    ped_diff = current_ped - prev_ped
    ped_perc = (ped_diff / prev_ped * 100) if prev_ped > 0 else 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("vs. Período Anterior")
        st.metric("Faturamento", format_currency_br(current_fat), 
                 delta=f"{format_currency_br(fat_diff)} ({fat_perc:.1f}%)")
        st.metric("Pedidos", format_integer_br(current_ped), 
                 delta=f"{format_integer_br(ped_diff)} ({ped_perc:.1f}%)")

st.markdown("---")

# TABELA DETALHADA OTIMIZADA
st.header("📋 Dados Detalhados")

# Limitar número de linhas exibidas para melhor performance
max_rows = st.selectbox("Máximo de linhas:", [100, 500, 1000, 5000], index=1)

# Colunas essenciais para exibição
display_columns = [
    'Mês', 'Cidade', 'Estado', 'Produto', 'Unidades Compradas',
    'Pedidos com Produto', 'Faturamento do Produto'
]

# Ordenação
sort_options = {
    'Faturamento do Produto': 'Faturamento do Produto',
    'Unidades Compradas': 'Unidades Compradas',
    'Pedidos com Produto': 'Pedidos com Produto',
    'Mês': 'Mês'
}

sort_column = st.selectbox("Ordenar por:", list(sort_options.keys()))
sort_order = st.radio("Ordem:", ["Decrescente", "Crescente"], index=0)
ascending = sort_order == "Crescente"

# Aplicar ordenação e limitar linhas
df_display = df_filtrado.nlargest(max_rows, sort_options[sort_column]) if not ascending else df_filtrado.nsmallest(max_rows, sort_options[sort_column])
df_display = df_display[display_columns].copy()

# Formatação otimizada
df_display['Mês'] = df_display['Mês'].dt.strftime('%Y-%m')
df_display['Faturamento do Produto'] = df_display['Faturamento do Produto'].apply(format_currency_br)
df_display['Unidades Compradas'] = df_display['Unidades Compradas'].apply(format_integer_br)
df_display['Pedidos com Produto'] = df_display['Pedidos com Produto'].apply(format_integer_br)

st.dataframe(df_display, use_container_width=True, hide_index=True)

# DOWNLOAD OTIMIZADO
st.header("📥 Export de Dados")

if st.button("📥 Preparar Download"):
    with st.spinner("Preparando arquivo..."):
        csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"dados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )