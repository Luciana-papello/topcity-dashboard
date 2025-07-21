import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import io
import urllib.parse 
# Assegure-se de que 'column_mapping.py' esteja na mesma pasta
from column_mapping import column_mapping 
import openai # NOVO: Importa a biblioteca OpenAI

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

# Definir as cores da marca Papello
PAPELLO_GREEN = '#96ca00' # Verde Papello
# Um tom mais escuro do verde para o degradê do título principal
PAPELLO_DARK_GREEN = '#4e9f00' # Cor do script do usuário para o main-header e metric-card


# Configuração da página
st.set_page_config(
    page_title="Dashboard TopCity",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para visual (mantido como no seu script)
st.markdown(f"""
<style>
    .metric-card {{
        background: linear-gradient(135deg, #96ca00 0%, #4e9f00 100%); /* Corrigido para verde */
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }}
    .metric-title {{
        font-size: 1.1em;
        margin-bottom: 0.5rem;
        opacity: 0.8;
    }}
    .metric-value {{
        font-size: 2.2em;
        font-weight: bold;
    }}
    .stMetric {{ /* Isso pode ser um seletor mais específico dependendo da versão do Streamlit */
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); /* Mantido do script do usuário */
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}
    .main-header {{
        background: linear-gradient(90deg, #96ca00 0%, #4e9f00  100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }}
    .chart-container {{
        padding: 1.5rem;
        background-color: #f8f9fa;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
    }}
    /* Estilo para os botões do Streamlit (ex: Resetar Filtros) */
    div.stButton > button {{
        background-color: #96ca00; /* Cor verde Papello */
        color: white; /* Cor do texto do botão */
        border-radius: 5px; /* Bordas arredondadas */
        border: 1px solid #96ca00; /* Borda da mesma cor */
        padding: 0.5em 1em; /* Espaçamento interno */
    }}

    /* Estilo para o botão ao passar o mouse */
    div.stButton > button:hover {{
        background-color: #6b8f00; /* Um verde um pouco mais escuro ao passar o mouse */
        color: white;
        border: 1px solid #6b8f00;
    }}        
    /* NOVO: Estilo para o container dos comparativos */
    .comparative-container-card {{
        background: linear-gradient(135deg, #96ca00 0%, #4e9f00 100%); /* Fundo verde para comparativos */
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }}
</style>
""", unsafe_allow_html=True)

# Título Principal do Dashboard
st.markdown("<h1 class='main-header'>Dashboard de Análise de Produtos e Cidades 🏙️</h1>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """
    Carrega e pré-processa os dados da planilha do Google Sheets.
    """
    # **IMPORTANTE**: Certifique-se que esta URL e o nome da aba estão corretos e a planilha é pública para leitura.
    sheet_id = '14Y-V3ezwo3LsHWERhSyURCtkQdN3drzv9F5JNRQnXEc' 
    tab_name = 'Produtos_Cidades_Completas'
    
    # INCLUÍDO: Codificar o nome da aba para garantir que a URL seja válida
    encoded_tab_name = urllib.parse.quote_plus(tab_name)
    google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_tab_name}"

    with st.spinner("Carregando dados... Por favor, aguarde."): 
        try:
            df = pd.read_csv(google_sheet_url)
        except Exception as e:
            st.error(f"Erro ao carregar dados da planilha do Google Sheets: {e}")
            st.warning("Por favor, verifique se o ID da planilha e o nome da aba estão corretos e se a planilha está compartilhada como 'Qualquer pessoa com o link'.")
            st.stop() 

    if df.empty:
        st.warning("A planilha do Google Sheets está vazia ou não contém dados. Verifique a planilha ou os filtros iniciais.")
        st.stop()

    # Convert 'mes' to datetime objects
    df['mes'] = pd.to_datetime(df['mes'], format='%Y-%m')

    # Conversão robusta de colunas numéricas:
    df.loc[:, 'faturamento'] = pd.to_numeric(df['faturamento'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    df.loc[:, 'faturamento_total_cidade_mes'] = pd.to_numeric(df['faturamento_total_cidade_mes'].astype(str).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
    
    df.loc[:, 'unidades_fisicas'] = pd.to_numeric(df['unidades_fisicas'], errors='coerce').fillna(0)
    df.loc[:, 'pedidos'] = pd.to_numeric(df['pedidos'], errors='coerce').fillna(0)
    df.loc[:, 'total_pedidos_cidade_mes'] = pd.to_numeric(df['total_pedidos_cidade_mes'], errors='coerce').fillna(0)

    # Renomear colunas para nomes amigáveis usando o mapping importado
    df = df.rename(columns=column_mapping)

    # Calcular Métricas Derivadas usando os nomes de coluna já renomeados
    df.loc[:, 'Participação Faturamento Cidade Mês (%)'] = np.where(
        df['Faturamento Total da Cidade no Mês'] == 0,
        0,
        (df['Faturamento do Produto'] / df['Faturamento Total da Cidade no Mês']) * 100
    )

    df.loc[:, 'Participação Pedidos Cidade Mês (%)'] = np.where(
        df['Total de Pedidos da Cidade no Mês'] == 0,
        0,
        (df['Pedidos com Produto'] / df['Total de Pedidos da Cidade no Mês']) * 100
    )

    df.loc[:, 'Ticket Médio do Produto'] = np.where(
        df['Pedidos com Produto'] == 0,
        0,
        df['Faturamento do Produto'] / df['Pedidos com Produto']
    )
    return df

df = load_data()

# --- Definir os estados iniciais dos filtros para o botão Reset ---
# INCLUÍDO/AJUSTADO: Lógica de inicialização de session_state para reset robusto
# Esta seção precisa estar antes dos filtros para que os defaults funcionem
if 'default_filters_set' not in st.session_state:
    st.session_state.default_months = sorted(df['Mês'].dt.to_period('M').unique().to_timestamp().tolist())
    st.session_state.default_estados = sorted(df['Estado'].unique())
    st.session_state.default_cidades = sorted(df['Cidade'].unique())
    st.session_state.default_produtos = [] 
    st.session_state.default_prod_evol_months = st.session_state.default_months
    st.session_state.default_filters_set = True
    # Inicializa as variáveis de estado para o detalhamento do Top N
    st.session_state.selected_detail_type = None
    st.session_state.selected_detail_name = None
    # Inicializa as chaves dos selectbox de detalhe para que o .get() funcione
    st.session_state.select_product_detail = 'Selecione um Produto'
    st.session_state.select_city_detail = 'Selecione uma Cidade'
    st.session_state.select_state_detail = 'Selecione um Estado'


def reset_filters():
    st.info("DEBUG: Botão Reset acionado.") 
    # INCLUÍDO/AJUSTADO: Deleta as chaves de session_state relacionadas aos filtros para forçar o reset
    filter_keys = ['selected_months', 'selected_estados', 'selected_cidades', 
                   'selected_produtos', 'selected_prod_evol_months', 
                   'select_product_detail', 'select_city_detail', 'select_state_detail', 
                   'selected_detail_type', 'selected_detail_name'] 
    
    for key in filter_keys:
        if key in st.session_state:
            del st.session_state[key]
            st.info(f"DEBUG: Deletado st.session_state['{key}']") 
    
    st.rerun() # AJUSTADO: Usar st.rerun() para compatibilidade


# --- Sidebar para Filtros ---
st.sidebar.header("⚙️ Filtros Globais")

# Botão Resetar Filtros
st.sidebar.button("🔄 Resetar Filtros", on_click=reset_filters)

# Filtro de Mês global (st.multiselect)
min_date = df['Mês'].min()
max_date = df['Mês'].max()

available_months = sorted(df['Mês'].dt.to_period('M').unique().to_timestamp().tolist())

# Usar st.session_state para o valor do filtro
# AJUSTADO: Usa .get para pegar o valor do session_state ou o default_months se não houver nada
selected_months = st.sidebar.multiselect(
    "Selecione o(s) Mês(es)",
    options=available_months,
    default=st.session_state.get('selected_months', st.session_state.default_months),
    format_func=lambda x: x.strftime('%Y-%m'),
    key='selected_months' # Chave para o session_state
)


# Filtro de Estado
all_estados = sorted(df['Estado'].unique())
# AJUSTADO: Pega o default do session_state ou o default inicial
selected_estados = st.sidebar.multiselect(
    "Selecione o(s) Estado(s)",
    options=all_estados,
    default=st.session_state.get('selected_estados', st.session_state.default_estados),
    key='selected_estados'
)

# Filtro de Cidade (dependente do estado)
if selected_estados:
    available_cidades = sorted(df[df['Estado'].isin(selected_estados)]['Cidade'].unique())
else:
    available_cidades = sorted(df['Cidade'].unique())
# AJUSTADO: Pega o default do session_state ou o default inicial
selected_cidades = st.sidebar.multiselect(
    "Selecione a(s) Cidade(s)",
    options=available_cidades,
    default=st.session_state.get('selected_cidades', st.session_state.default_cidades),
    key='selected_cidades'
)

# Filtro de Produto
all_produtos = sorted(df['Produto'].unique())
# AJUSTADO: Pega o default do session_state ou o default inicial (que é [])
selected_produtos = st.sidebar.multiselect(
    "Selecione o(s) Produto(s)",
    options=all_produtos,
    default=st.session_state.get('selected_produtos', st.session_state.default_produtos),
    key='selected_produtos'
)

# --- Aplica os Filtros Globais ---
df_filtrado = df.copy()

if selected_months: 
    df_filtrado = df_filtrado[df_filtrado['Mês'].isin(selected_months)]

if selected_estados:
    df_filtrado = df_filtrado[df_filtrado['Estado'].isin(selected_estados)]

if selected_cidades:
    df_filtrado = df_filtrado[df_filtrado['Cidade'].isin(selected_cidades)]

# INCLUÍDO: Aplica o filtro global de cidade/estado acionado pelo clique nos Top N (se houver)
# Este bloco de filtro deve vir antes do filtro de produto
if st.session_state.selected_detail_type == 'Cidade' and st.session_state.selected_detail_name:
    # APLICA FILTRO GLOBAL ACIONADO PELO DETALHAMENTO
    df_filtrado = df_filtrado[df_filtrado['Cidade'] == st.session_state.selected_detail_name]
    st.info(f"DEBUG: Dados filtrados por detalhe de Cidade: {st.session_state.selected_detail_name}")
elif st.session_state.selected_detail_type == 'Estado' and st.session_state.selected_detail_name:
    # APLICA FILTRO GLOBAL ACIONADO PELO DETALHAMENTO
    df_filtrado = df_filtrado[df_filtrado['Estado'] == st.session_state.selected_detail_name]
    st.info(f"DEBUG: Dados filtrados por detalhe de Estado: {st.session_state.selected_detail_name}")


if selected_produtos:
    df_filtrado = df_filtrado[df_filtrado['Produto'].isin(selected_produtos)]


if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados. Tente ajustar os filtros.")
    st.stop()

# --- Painel de Definições/Glossário ---
st.expander_title = "📚 Definições das Métricas"
with st.expander(st.expander_title):
    st.markdown("""
    * **Faturamento Total:** Soma do `Faturamento Total da Cidade no Mês` (se nenhum produto for filtrado) ou soma do `Faturamento do Produto` (se produtos forem filtrados), dentro dos filtros aplicados.
    * **Total Pedidos:** Soma do `Total de Pedidos da Cidade no Mês` (se nenhum produto for filtrado) ou soma de `Pedidos com Produto` (se produtos forem filtrados), dentro dos filtros aplicados.
    * **Unidades Compradas:** Soma total das unidades físicas de produtos vendidos.
    * **Ticket Médio Geral:** Faturamento Total dividido pelo Total de Pedidos.
    * **% Partic. Faturamento Prod. (Méd.):** A média das participações percentuais do faturamento de cada produto em relação ao faturamento total da cidade onde ele foi vendido.
    * **Faturamento do Produto:** Faturamento gerado por um produto específico na cidade/mês (valor por linha).
    * **Faturamento Total da Cidade no Mês:** Faturamento total da cidade em um dado mês, de todos os pedidos e produtos.
    * **Pedidos com Produto:** Quantidade de pedidos que incluíram um produto específico.
    * **Total de Pedidos da Cidade no Mês:** Quantidade total de pedidos que a cidade teve em um dado mês, independente do produto.
    * **Ticket Médio do Produto:** Faturamento de um produto dividido pelo número de pedidos que o continham.
    """)
st.markdown("---")


# --- KPIs no Topo ---
st.header("📊 Principais Indicadores")

# Usar um container para agrupar as métricas de KPI e garantir o layout
st.markdown("<div class='kpi-container'>", unsafe_allow_html=True) 
with st.container():
    # Lógica condicional para KPIs de Faturamento Total e Total Pedidos
    if selected_produtos:
        total_faturamento = df_filtrado['Faturamento do Produto'].sum()
        total_pedidos_kpi = df_filtrado['Pedidos com Produto'].sum()
    else:
        df_kpi_base = df_filtrado.groupby(['Mês', 'Cidade']).agg(
            total_pedidos_cidade_mes=('Total de Pedidos da Cidade no Mês', 'first'),
            faturamento_total_cidade_mes=('Faturamento Total da Cidade no Mês', 'first')
        ).reset_index()
        total_faturamento = df_kpi_base['faturamento_total_cidade_mes'].sum()
        total_pedidos_kpi = df_kpi_base['total_pedidos_cidade_mes'].sum()


    total_unidades_fisicas = df_filtrado['Unidades Compradas'].sum()

    # Calcula Ticket Médio Geral com base nos totais
    ticket_medio_geral = total_faturamento / total_pedidos_kpi if total_pedidos_kpi > 0 else 0

    # Participação do produto no faturamento total da cidade (em %)
    media_participacao_faturamento = df_filtrado['Participação Faturamento Cidade Mês (%)'].mean()


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
        <div class="metric-title">Ticket Médio Geral</div>
        <div class="metric-value">{format_currency_br(ticket_medio_geral)}</div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="metric-title">% Partic. Faturamento Prod. (Méd.)</div>
        <div class="metric-value">{media_participacao_faturamento:,.2f}%</div>
        """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True) # Fechar o container dos KPIs

st.markdown("---")

# --- Análise de Desempenho (Produtos, Cidades, Estados) ---
st.header("📈 Análise de Desempenho")

tab_produtos, tab_cidades, tab_estados = st.tabs(["Top Produtos", "Top Cidades", "Top Estados"])

with tab_produtos:
    st.subheader("Top Produtos por Métrica")
    metric_produto = st.selectbox(
        "Selecionar Métrica para Top Produtos:",
        options=["Faturamento do Produto", "Unidades Compradas"]
    )
    n_produtos = st.slider("Número de Produtos no Top N:", min_value=5, max_value=20, value=10)

    # Garante que a soma é numérica para nlargest
    top_produtos = df_filtrado.groupby('Produto')[metric_produto].sum().astype(float).nlargest(n_produtos).reset_index()
    top_produtos.columns = ['Produto', 'Total']

    fig_top_produtos = px.bar(
        top_produtos,
        x='Total',
        y='Produto',
        orientation='h',
        title=f"Top {n_produtos} Produtos por {metric_produto}",
        labels={'Total': metric_produto, 'Produto': 'Nome do Produto'},
        color='Total', 
        color_continuous_scale=px.colors.sequential.Plasma # Escala de cor padrão
    )
    # Formatação do eixo X e TOOLTIP
    if metric_produto == "Faturamento do Produto":
        fig_top_produtos.update_xaxes(tickprefix="R$ ", tickformat=",.2f") 
        fig_top_produtos.update_traces(hovertemplate='Produto: %{y}<br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    elif metric_produto == "Unidades Compradas":
        fig_top_produtos.update_xaxes(tickformat=",f") 
        fig_top_produtos.update_traces(hovertemplate='Produto: %{y}<br>Unidades: %{x:,f}<extra></extra>')
        
    fig_top_produtos.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top_produtos, use_container_width=True)

    # NOVO: Seletor para Detalhamento de Produto (para abrir seção de detalhes ABAIXO)
    if not top_produtos.empty:
        # Pega a seleção atual ou o valor padrão (primeiro item ou "Selecione...")
        product_detail_options = ['Selecione um Produto'] + top_produtos['Produto'].tolist()
        # default_index precisa ser 0 (para "Selecione...") se não houver seleção prévia
        default_index_product = 0
        if 'selected_detail_type' in st.session_state and st.session_state.selected_detail_type == 'Produto':
            try:
                default_index_product = product_detail_options.index(st.session_state.selected_detail_name)
            except ValueError: # Caso o produto detalhado não esteja nas opções atuais
                default_index_product = 0 
        
        selected_product_to_detail = st.selectbox(
            "Detalhar Produto:",
            options=product_detail_options,
            index=default_index_product, 
            key='select_product_detail'
        )
        if selected_product_to_detail != 'Selecione um Produto':
            # Atualiza o estado da sessão para exibir a seção de detalhes
            # Nao força rerun aqui se o estado já está setado, apenas se mudou
            if (st.session_state.selected_detail_type != 'Produto' or 
                st.session_state.selected_detail_name != selected_product_to_detail):
                st.session_state.selected_detail_type = 'Produto'
                st.session_state.selected_detail_name = selected_product_to_detail
                st.rerun() # AJUSTADO: Usar st.rerun() para compatibilidade


    st.subheader("Evolução do Desempenho dos Produtos ao Longo do Tempo")
    
    # Filtro de Data INDIVIDUAL para a Evolução de Produtos (multiselect de meses)
    all_months_prod_evol = sorted(df['Mês'].dt.to_period('M').unique().to_timestamp().tolist())

    selected_prod_evol_months = st.multiselect(
        "Selecione o(s) Mês(es) para Evolução dos Produtos",
        options=all_months_prod_evol,
        default=st.session_state.get('selected_prod_evol_months', all_months_prod_evol), 
        format_func=lambda x: x.strftime('%Y-%m'),
        key='selected_prod_evol_months'
    )

    df_filtered_for_prod_evol = df.copy()

    # Aplica o filtro de meses selecionados para a evolução
    if selected_prod_evol_months:
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Mês'].isin(selected_prod_evol_months)]
    
    # Aplica os filtros GLOBAIS de Cidade/Estado/Produto ao df_filtered_for_prod_evol também
    if selected_estados:
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Estado'].isin(selected_estados)]
    if selected_cidades:
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Cidade'].isin(selected_cidades)]

    if selected_produtos: 
        df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Produto'].isin(selected_produtos)]
    elif not top_produtos.empty: 
         df_filtered_for_prod_evol = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Produto'].isin(top_produtos['Produto'].tolist())]
    
    if df_filtered_for_prod_evol.empty:
        st.info("Nenhum dado para mostrar na evolução de produtos com os filtros selecionados.")
    else:
        produtos_para_linha_options = sorted(df_filtered_for_prod_evol['Produto'].unique())
        
        default_prod_evol_selection_multiselect = [p for p in sorted(top_produtos['Produto'].tolist()[:3]) if p in produtos_para_linha_options]

        produtos_para_linha = st.multiselect(
            "Selecione Produtos para o Gráfico de Linha (máx 5):",
            options=produtos_para_linha_options,
            default=default_prod_evol_selection_multiselect
        )

        if produtos_para_linha:
            df_produtos_tempo = df_filtered_for_prod_evol[df_filtered_for_prod_evol['Produto'].isin(produtos_para_linha)].groupby(['Mês', 'Produto']).agg(
                faturamento=('Faturamento do Produto', 'sum'),
                unidades_compradas=('Unidades Compradas', 'sum')
            ).reset_index()

            fig_prod_tempo_fat = px.line(
                df_produtos_tempo,
                x='Mês',
                y='faturamento',
                color='Produto',
                title='Faturamento dos Produtos Selecionados ao Longo do Tempo',
                labels={'Mês': 'Mês', 'faturamento': 'Faturamento', 'Produto': 'Produto'},
                line_shape='linear',
                color_discrete_sequence=px.colors.qualitative.Plotly # Escala de cor padrão
            )
            fig_prod_tempo_fat.update_xaxes(dtick="M1", tickformat="%Y-%m")
            fig_prod_tempo_fat.update_yaxes(tickprefix="R$ ", tickformat=",.2f") 
            fig_prod_tempo_fat.update_traces(hovertemplate='Mês: %{x|%Y-%m}<br>Produto: %{fullData.name}<br>Faturamento: R$ %{y:,.2f}<extra></extra>')
            st.plotly_chart(fig_prod_tempo_fat, use_container_width=True)

            fig_prod_tempo_unid = px.line(
                df_produtos_tempo,
                x='Mês',
                y='unidades_compradas',
                color='Produto',
                title='Unidades Compradas dos Produtos Selecionados ao Longo do Tempo',
                labels={'Mês': 'Mês', 'unidades_compradas': 'Unidades Compradas', 'Produto': 'Produto'},
                line_shape='linear',
                color_discrete_sequence=px.colors.qualitative.Plotly # Escala de cor padrão
            )
            fig_prod_tempo_unid.update_xaxes(dtick="M1", tickformat="%Y-%m")
            fig_prod_tempo_unid.update_yaxes(tickformat=",f") 
            fig_prod_tempo_unid.update_traces(hovertemplate='Mês: %{x|%Y-%m}<br>Produto: %{fullData.name}<br>Unidades: %{y:,f}<extra></extra>')
            st.plotly_chart(fig_prod_tempo_unid, use_container_width=True)
        else:
            st.info("Selecione os produtos para ver a evolução ao longo do tempo.")

with tab_cidades:
    st.subheader("Top Cidades por Métrica")
    metric_cidade = st.selectbox(
        "Selecionar Métrica para Top Cidades:",
        options=["Faturamento Total da Cidade no Mês", "Unidades Compradas", "Pedidos com Produto"]
    )
    n_cidades = st.slider("Número de Cidades no Top N:", min_value=5, max_value=20, value=10)

    # Agregação correta para Top Cidades por Faturamento (condicional)
    if selected_produtos: 
        if metric_cidade == "Faturamento Total da Cidade no Mês":
            top_cidades = df_filtrado.groupby('Cidade')['Faturamento do Produto'].sum().astype(float).nlargest(n_cidades).reset_index()
        elif metric_cidade == "Unidades Compradas":
            top_cidades = df_filtrado.groupby('Cidade')['Unidades Compradas'].sum().astype(float).nlargest(n_cidades).reset_index()
        else: # Pedidos com Produto
            top_cidades = df_filtrado.groupby('Cidade')['Pedidos com Produto'].sum().astype(float).nlargest(n_cidades).reset_index()
    else: # Se nenhum produto é filtrado, use os totais da cidade
        if metric_cidade == "Faturamento Total da Cidade no Mês":
            top_cidades_agg = df_filtrado.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().reset_index()
            top_cidades = top_cidades_agg.groupby('Cidade')['Faturamento Total da Cidade no Mês'].sum().astype(float).nlargest(n_cidades).reset_index()
        elif metric_cidade == "Unidades Compradas":
            top_cidades = df_filtrado.groupby('Cidade')['Unidades Compradas'].sum().astype(float).nlargest(n_cidades).reset_index()
        else: # Pedidos com Produto
            top_cidades = df_filtrado.groupby('Cidade')['Pedidos com Produto'].sum().astype(float).nlargest(n_cidades).reset_index()


    top_cidades.columns = ['Cidade', 'Total'] 
    fig_top_cidades = px.bar(
        top_cidades,
        x='Total',
        y='Cidade',
        orientation='h',
        title=f"Top {n_cidades} Cidades por {metric_cidade}",
        labels={'Total': metric_cidade, 'Cidade': 'Nome do Cidade'},
        color='Total',
        color_continuous_scale=px.colors.sequential.Viridis # Escala de cor padrão
    )
    # Formatação do eixo X e TOOLTIP
    if metric_cidade == "Faturamento Total da Cidade no Mês":
        fig_top_cidades.update_xaxes(tickprefix="R$ ", tickformat=",.2f") 
        fig_top_cidades.update_traces(hovertemplate='Cidade: %{y}<br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    elif metric_cidade == "Unidades Compradas":
        fig_top_cidades.update_xaxes(tickformat=",f") 
        fig_top_cidades.update_traces(hovertemplate='Cidade: %{y}<br>Unidades: %{x:,f}<extra></extra>')
    elif metric_cidade == "Pedidos com Produto":
        fig_top_cidades.update_xaxes(tickformat=",f") 
        fig_top_cidades.update_traces(hovertemplate='Cidade: %{y}<br>Pedidos: %{x:,f}<extra></extra>')
        
    fig_top_cidades.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top_cidades, use_container_width=True)

    # NOVO: Seletor para Detalhamento de Cidade
    if not top_cidades.empty:
        city_detail_options = ['Selecione uma Cidade'] + top_cidades['Cidade'].tolist()
        default_index_city = 0 # Valor padrão para "Selecione uma Cidade"
        if 'selected_detail_type' in st.session_state and st.session_state.selected_detail_type == 'Cidade':
            try:
                default_index_city = city_detail_options.index(st.session_state.selected_detail_name)
            except ValueError:
                default_index_city = 0 # Caso a cidade detalhada não esteja nas opções atuais

        selected_city_to_detail = st.selectbox(
            "Detalhar Cidade:",
            options=city_detail_options,
            index=default_index_city, 
            key='select_city_detail'
        )
        if selected_city_to_detail != 'Selecione uma Cidade':
            if (st.session_state.selected_detail_type != 'Cidade' or 
                st.session_state.selected_detail_name != selected_city_to_detail):
                st.session_state.selected_detail_type = 'Cidade'
                st.session_state.selected_detail_name = selected_city_to_detail
                st.rerun() # AJUSTADO: Usar st.rerun() para compatibilidade


with tab_estados:
    st.subheader("Top Estados por Métrica")
    metric_estado = st.selectbox(
        "Selecionar Métrica para Top Estados:",
        options=["Faturamento Total da Cidade no Mês", "Unidades Compradas", "Pedidos com Produto"]
    )
    n_estados = st.slider("Número de Estados no Top N:", min_value=5, max_value=20, value=10)

    # Agregação correta para Top Estados por Métrica (condicional)
    if selected_produtos: 
        if metric_estado == "Faturamento Total da Cidade no Mês":
            top_estados = df_filtrado.groupby('Estado')['Faturamento do Produto'].sum().astype(float).nlargest(n_estados).reset_index()
        elif metric_estado == "Unidades Compradas":
            top_estados = df_filtrado.groupby('Estado')['Unidades Compradas'].sum().astype(float).nlargest(n_estados).reset_index()
        else: # Pedidos com Produto
            top_estados = df_filtrado.groupby('Estado')['Pedidos com Produto'].sum().astype(float).nlargest(n_estados).reset_index()
    else: # Se nenhum produto é filtrado, use os totais do estado
        if metric_estado == "Faturamento Total da Cidade no Mês":
            top_estados_agg = df_filtrado.groupby(['Mês', 'Estado'])['Faturamento Total da Cidade no Mês'].first().reset_index()
            top_estados = top_estados_agg.groupby('Estado')['Faturamento Total da Cidade no Mês'].sum().astype(float).nlargest(n_estados).reset_index()
        elif metric_estado == "Unidades Compradas":
            top_estados = df_filtrado.groupby('Estado')['Unidades Compradas'].sum().astype(float).nlargest(n_estados).reset_index()
        else: # Pedidos com Produto
            top_estados = df_filtrado.groupby('Estado')['Pedidos com Produto'].sum().astype(float).nlargest(n_estados).reset_index()

    top_estados.columns = ['Estado', 'Total'] 
    fig_top_estados = px.bar(
        top_estados,
        x='Total',
        y='Estado',
        orientation='h',
        title=f"Top {n_estados} Estados por {metric_estado}",
        labels={'Total': metric_estado, 'Estado': 'Nome do Estado'},
        color='Total',
        color_continuous_scale=px.colors.sequential.Cividis # Escala de cor padrão
    )
    # Formatação do eixo X e TOOLTIP
    if metric_estado == "Faturamento Total da Cidade no Mês":
        fig_top_estados.update_xaxes(tickprefix="R$ ", tickformat=",.2f") 
        fig_top_estados.update_traces(hovertemplate='Estado: %{y}<br>Faturamento: R$ %{x:,.2f}<extra></extra>')
    elif metric_estado == "Unidades Compradas":
        fig_top_estados.update_xaxes(tickformat=",f") 
        fig_top_estados.update_traces(hovertemplate='Estado: %{y}<br>Unidades: %{x:,f}<extra></extra>')
    elif metric_estado == "Pedidos com Produto":
        fig_top_estados.update_xaxes(tickformat=",f") 
        fig_top_estados.update_traces(hovertemplate='Estado: %{y}<br>Pedidos: %{x:,f}<extra></extra>')
        
    fig_top_estados.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_top_estados, use_container_width=True)

    # Seletor para Detalhamento de Estado
    if not top_estados.empty:
        state_detail_options = ['Selecione um Estado'] + top_estados['Estado'].tolist()
        default_index_state = 0 # Valor padrão para "Selecione um Estado"
        if 'selected_detail_type' in st.session_state and st.session_state.selected_detail_type == 'Estado':
            try:
                default_index_state = state_detail_options.index(st.session_state.selected_detail_name)
            except ValueError:
                default_index_state = 0 # Caso o estado detalhado não esteja nas opções atuais

        selected_state_to_detail = st.selectbox(
            "Detalhar Estado:",
            options=state_detail_options,
            index=default_index_state, 
            key='select_state_detail'
        )
        if selected_state_to_detail != 'Selecione um Estado':
            if (st.session_state.selected_detail_type != 'Estado' or 
                st.session_state.selected_detail_name != selected_state_to_detail):
                st.session_state.selected_detail_type = 'Estado'
                st.session_state.selected_detail_name = selected_state_to_detail
                st.rerun() # AJUSTADO: Usar st.rerun() para compatibilidade


st.markdown("---")

# --- Comparativos de Período ---
st.header("🔄 Comparativos de Período")

# Use um container para agrupar as métricas de comparação e garantir o layout
st.markdown("<div class='comparative-container-card'>", unsafe_allow_html=True) # Abertura do container com a classe CSS

if selected_months:
    # INCLUÍDO: Inicializa todas as variáveis de cálculo para evitar NameError
    current_faturamento_base_comp = 0.0
    current_pedidos_base_comp = 0.0
    previous_faturamento_base_comp = 0.0
    previous_pedidos_base_comp = 0.0
    three_months_faturamento_base_comp = 0.0
    three_months_pedidos_base_comp = 0.0
    fat_diff_prev = 0.0
    fat_perc_prev = 0.0
    ped_diff_prev = 0.0
    ped_perc_prev = 0.0
    avg_3m_faturamento_display = 0.0
    avg_3m_pedidos_display = 0.0
    fat_diff_3m = 0.0
    fat_perc_3m = 0.0
    ped_diff_3m = 0.0
    ped_perc_3m = 0.0
    
    # Cria as colunas dentro do container
    col_comp1, col_comp2 = st.columns(2) 

    # Base para comparativos: df original (não filtrado), depois aplica os filtros
    df_base_comp = df.copy() 
    if selected_cidades:
        df_base_comp = df_base_comp[df_base_comp['Cidade'].isin(selected_cidades)]
    if selected_estados:
        df_base_comp = df_base_comp[df_base_comp['Estado'].isin(selected_estados)]
    
    # Condição para faturamento e pedidos: se houver produto selecionado, usa métricas de produto
    if selected_produtos:
        st.info("DEBUG: Comparativos calculados usando 'Faturamento do Produto' e 'Pedidos com Produto' (produto(s) selecionado(s)).")
        
        df_current_period_for_comp = df_base_comp[(df_base_comp['Mês'] >= min(selected_months)) & (df_base_comp['Mês'] <= max(selected_months)) & \
                                                  df_base_comp['Produto'].isin(selected_produtos)]
        df_previous_month = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=1))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1))) & \
                                             df_base_comp['Produto'].isin(selected_produtos)]
        df_three_months_ago = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=3))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1))) & \
                                          df_base_comp['Produto'].isin(selected_produtos)]
        
        current_faturamento_base_comp = df_current_period_for_comp['Faturamento do Produto'].sum()
        current_pedidos_base_comp = df_current_period_for_comp['Pedidos com Produto'].sum()

        previous_faturamento_base_comp = df_previous_month['Faturamento do Produto'].sum()
        previous_pedidos_base_comp = df_previous_month['Pedidos com Produto'].sum()

        three_months_faturamento_base_comp = df_three_months_ago['Faturamento do Produto'].sum()
        three_months_pedidos_base_comp = df_three_months_ago['Pedidos com Produto'].sum()

    else: # Se nenhum produto for selecionado, usa faturamento total da cidade
        st.info("DEBUG: Comparativos calculados usando 'Faturamento Total da Cidade no Mês' e 'Total de Pedidos da Cidade no Mês'.")

        df_current_period_for_comp = df_base_comp[(df_base_comp['Mês'] >= min(selected_months)) & (df_base_comp['Mês'] <= max(selected_months))]
        df_previous_month = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=1))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1)))]
        df_three_months_ago = df_base_comp[(df_base_comp['Mês'] >= (min(selected_months) - pd.DateOffset(months=3))) & (df_base_comp['Mês'] <= (min(selected_months) - pd.DateOffset(days=1)))]
        
        # Agregações para o período (faturamento total da cidade)
        current_faturamento_base_comp = df_current_period_for_comp.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
        current_pedidos_base_comp = df_current_period_for_comp.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

        previous_faturamento_base_comp = df_previous_month.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
        previous_pedidos_base_comp = df_previous_month.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()

        three_months_faturamento_base_comp = df_three_months_ago.groupby(['Mês', 'Cidade'])['Faturamento Total da Cidade no Mês'].first().sum()
        three_months_pedidos_base_comp = df_three_months_ago.groupby(['Mês', 'Cidade'])['Total de Pedidos da Cidade no Mês'].first().sum()
        
    # Mensagens de depuração para o cálculo da média dos 3 meses
    st.info(f"DEBUG: df_three_months_ago shape: {df_three_months_ago.shape}")
    st.info(f"DEBUG: three_months_pedidos_base_comp (SUM): {three_months_pedidos_base_comp}")
    num_unique_months_3m_with_data = len(df_three_months_ago['Mês'].dt.to_period('M').unique())
    st.info(f"DEBUG: num_unique_months_3m_with_data (DIVISOR): {num_unique_months_3m_with_data}")

    # A média dos 3 meses é dividida pelo número de meses ÚNICOS COM DADOS, com segurança contra divisão por zero
    avg_3m_faturamento_display = (three_months_faturamento_base_comp / num_unique_months_3m_with_data) if num_unique_months_3m_with_data > 0 else 0
    avg_3m_pedidos_display = (three_months_pedidos_base_comp / num_unique_months_3m_with_data) if num_unique_months_3m_with_data > 0 else 0
    st.info(f"DEBUG: avg_3m_pedidos_display (FINAL AVG): {avg_3m_pedidos_display}")


    fat_diff_3m = current_faturamento_base_comp - avg_3m_faturamento_display
    fat_perc_3m = (fat_diff_3m / avg_3m_faturamento_display * 100) if avg_3m_faturamento_display > 0 else 0

    ped_diff_3m = current_pedidos_base_comp - avg_3m_pedidos_display
    ped_perc_3m = (ped_diff_3m / avg_3m_pedidos_display * 100) if avg_3m_pedidos_display > 0 else 0

    with col_comp1:
        st.subheader("Período Selecionado vs. Período Anterior")
        st.metric(label="Faturamento", value=format_currency_br(current_faturamento_base_comp), delta=f"{format_currency_br(fat_diff_prev)} ({fat_perc_prev:,.2f}%)")
        st.metric(label="Total Pedidos", value=format_integer_br(current_pedidos_base_comp), delta=f"{format_integer_br(ped_diff_prev)} ({ped_perc_prev:,.2f}%)")

    with col2:
        st.subheader("Período Selecionado vs. Média Últimos 3 Meses")
        st.metric(label="Faturamento", value=format_currency_br(current_faturamento_base_comp), delta=f"{format_currency_br(fat_diff_3m)} ({fat_perc_3m:,.2f}%)")
        st.metric(label="Total Pedidos", value=format_integer_br(avg_3m_pedidos_display), delta=f"{format_integer_br(ped_diff_3m)} ({ped_perc_3m:,.2f}%)")

else:
    st.info("Selecione pelo menos um mês nos filtros globais para ver os comparativos de período.")
    
st.markdown("</div>", unsafe_allow_html=True) # Fechar o container do comparativo

st.markdown("---")

# --- Tabela Detalhada ---
st.header("📋 Dados Detalhados")

# Colunas que o usuário quer ver na tabela (agora com nomes amigáveis)
columns_to_display = [
    'Mês', 'Cidade', 'Estado', 'Produto', 'Unidades Compradas',
    'Pedidos com Produto', 'Faturamento do Produto', 'Participação Faturamento Cidade Mês (%)',
    'Participação Pedidos Cidade Mês (%)', 'Ticket Médio do Produto'
]

# Opção de ordenação
sort_column_options = {
    'Mês': 'Mês',
    'Cidade': 'Cidade',
    'Estado': 'Estado',
    'Produto': 'Produto',
    'Unidades Compradas': 'Unidades Compradas',
    'Pedidos com Produto': 'Pedidos com Produto',
    'Faturamento do Produto': 'Faturamento do Produto',
    'Ticket Médio do Produto': 'Ticket Médio do Produto',
    'Participação Faturamento Cidade Mês (%)': 'Participação Faturamento Cidade Mês (%)',
    'Participação Pedidos Cidade Mês (%)': 'Participação Pedidos Cidade Mês (%)'
}
sort_column_display = st.selectbox(
    "Ordenar Tabela Por:",
    options=list(sort_column_options.keys()),
    index=list(sort_column_options.keys()).index('Faturamento do Produto')
)
sort_column_actual = sort_column_options[sort_column_display] # Obtém o nome da coluna real para ordenação

sort_order = st.radio("Ordem:", options=["Decrescente", "Crescente"], index=0)
ascending = True if sort_order == "Crescente" else False

# Ordenar o DataFrame filtrado ANTES de formatar para exibição
df_sorted = df_filtrado.sort_values(by=sort_column_actual, ascending=ascending)

# Agora, selecione as colunas para exibição e formate
df_exibir_formatted = df_sorted[columns_to_display].copy()
df_exibir_formatted['Mês'] = df_exibir_formatted['Mês'].dt.strftime('%Y-%m')
df_exibir_formatted['Faturamento do Produto'] = df_exibir_formatted['Faturamento do Produto'].apply(format_currency_br)
df_exibir_formatted['Participação Faturamento Cidade Mês (%)'] = df_exibir_formatted['Participação Faturamento Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
df_exibir_formatted['Participação Pedidos Cidade Mês (%)'] = df_exibir_formatted['Participação Pedidos Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
df_exibir_formatted['Ticket Médio do Produto'] = df_exibir_formatted['Ticket Médio do Produto'].apply(format_currency_br)
df_exibir_formatted['Unidades Compradas'] = df_exibir_formatted['Unidades Compradas'].apply(format_integer_br)
df_exibir_formatted['Pedidos com Produto'] = df_exibir_formatted['Pedidos com Produto'].apply(format_integer_br)

st.dataframe(
    df_exibir_formatted,
    use_container_width=True,
    hide_index=True
)

# Download dos dados
st.header("📥 Export de Dados")

col1, col2 = st.columns(2)

with col1:
    if not df_filtrado.empty:
        # Botões de Download CSV e Excel para Dados Filtrados
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV Dados Filtrados",
            data=csv,
            file_name=f"dados_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        excel_buffer = io.BytesIO()
        df_filtrado.to_excel(excel_buffer, index=False, sheet_name='Dados Filtrados')
        excel_buffer.seek(0) # Volta ao início do buffer
        st.download_button(
            label="📥 Download XLSX Dados Filtrados",
            data=excel_buffer.getvalue(),
            file_name=f"dados_filtrados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


with col2:
    if not df_filtrado.empty:
        # Resumo executivo (agregado pelos filtros aplicados)
        resumo = df_filtrado.groupby(['Mês', 'Cidade', 'Estado']).agg(
            faturamento_total_produtos_selecionados=('Faturamento do Produto', 'sum'),
            unidades_compradas_total_produtos_selecionadas=('Unidades Compradas', 'sum'), 
            pedidos_com_produto_selecionado=('Pedidos com Produto', 'sum'),
            total_pedidos_cidade_mes_unique=('Total de Pedidos da Cidade no Mês', 'first'),
            faturamento_total_cidade_mes_unique=('Faturamento Total da Cidade no Mês', 'first')
        ).reset_index()

        # CRITICAL FIX: Ensure columns exist in 'resumo' after aggregation, especially for empty/NaN groups
        expected_agg_cols = ['faturamento_total_produtos_selecionados', 'unidades_compradas_total_produtos_selecionadas', 'pedidos_com_produto_selecionado', 
                             'total_pedidos_cidade_mes_unique', 'faturamento_total_cidade_mes_unique']
        for col in expected_agg_cols:
            if col not in resumo.columns:
                resumo[col] = 0.0 # Add missing column with default value if not created by agg

        # Recalcula participações e ticket médio para o resumo
        resumo['Participação Faturamento Cidade Mês (%)'] = np.where(
            resumo['faturamento_total_produtos_selecionados'] == 0,
            0,
            (resumo['faturamento_total_produtos_selecionados'] / resumo['faturamento_total_cidade_mes_unique']) * 100
        )
        resumo['Participação Pedidos Cidade Mês (%)'] = np.where(
            resumo['total_pedidos_cidade_mes_unique'] == 0,
            0,
            (resumo['pedidos_com_produto_selecionado'] / resumo['total_pedidos_cidade_mes_unique']) * 100
        )
        resumo['Ticket Médio Geral Cidade'] = np.where(
            resumo['pedidos_com_produto_selecionado'] == 0,
            0,
            resumo['faturamento_total_produtos_selecionados'] / resumo['pedidos_com_produto_selecionado']
        )
        
        # Selecionar e renomear colunas para o CSV de resumo
        resumo_final_cols = [
            'Mês', 'Cidade', 'Estado',
            'faturamento_total_produtos_selecionados',
            'unidades_compradas_total_produtos_selecionadas', 
            'pedidos_com_produto_selecionado',
            'total_pedidos_cidade_mes_unique',
            'faturamento_total_cidade_mes_unique',
            'Participação Faturamento Cidade Mês (%)',
            'Participação Pedidos Cidade Mês (%)',
            'Ticket Médio Geral Cidade'
        ]
        resumo_final = resumo[resumo_final_cols].rename(columns={
            'faturamento_total_produtos_selecionados': 'Faturamento Total Produtos Selecionados',
            'unidades_compradas_total_produtos_selecionadas': 'Unidades Compradas Produtos Selecionadas', 
            'pedidos_com_produto_selecionado': 'Pedidos com Produtos Selecionados',
            'total_pedidos_cidade_mes_unique': 'Total de Pedidos da Cidade no Mês',
            'faturamento_total_cidade_mes_unique': 'Faturamento Total da Cidade no Mês'
        })

        # Formata colunas para o CSV de resumo
        resumo_final['Mês'] = resumo_final['Mês'].dt.strftime('%Y-%m')
        resumo_final['Faturamento Total Produtos Selecionados'] = resumo_final['Faturamento Total Produtos Selecionados'].apply(format_currency_br)
        resumo_final['Unidades Compradas Produtos Selecionados'] = resumo_final['Unidades Compradas Produtos Selecionados'].apply(format_integer_br)
        resumo_final['Pedidos com Produtos Selecionados'] = resumo_final['Pedidos com Produtos Selecionados'].apply(format_integer_br)
        resumo_final['Total de Pedidos da Cidade no Mês'] = resumo_final['Total de Pedidos da Cidade no Mês'].apply(format_integer_br)
        resumo_final['Faturamento Total da Cidade no Mês'] = resumo_final['Faturamento Total da Cidade no Mês'].apply(format_currency_br)
        resumo_final['Participação Faturamento Cidade Mês (%)'] = resumo_final['Participação Faturamento Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
        resumo_final['Participação Pedidos Cidade Mês (%)'] = resumo_final['Participação Pedidos Cidade Mês (%)'].apply(lambda x: f"{x:,.2f}%")
        resumo_final['Ticket Médio Geral Cidade'] = resumo_final['Ticket Médio Geral Cidade'].apply(format_currency_br)

        csv_resumo = resumo_final.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Download CSV Resumo Executivo",
            data=csv_resumo,
            file_name=f"resumo_executivo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )