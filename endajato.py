import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
from typing import List, Dict, Optional, Any
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Consultor de Processos Judiciais",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CREDENCIAIS (MODO SIMPLIFICADO) ---
APP_PASSWORD = "senha123"  # <-- Sinta-se à vontade para trocar esta senha
DATAJUD_API_KEY = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# --- DICIONÁRIOS DE ENDPOINTS ---
ENDPOINTS = {
    "Justiça Estadual": {
        "01": "https://api-publica.datajud.cnj.jus.br/api_publica_tjac/_search",
        "02": "https://api-publica.datajud.cnj.jus.br/api_publica_tjal/_search",
        "03": "https://api-publica.datajud.cnj.jus.br/api_publica_tjap/_search",
        "04": "https://api-publica.datajud.cnj.jus.br/api_publica_tjam/_search",
        "05": "https://api-publica.datajud.cnj.jus.br/api_publica_tjba/_search",
        "06": "https://api-publica.datajud.cnj.jus.br/api_publica_tjce/_search",
        "07": "https://api-publica.datajud.cnj.jus.br/api_publica_tjdft/_search",
        "08": "https://api-publica.datajud.cnj.jus.br/api_publica_tjes/_search",
        "09": "https://api-publica.datajud.cnj.jus.br/api_publica_tjgo/_search",
        "10": "https://api-publica.datajud.cnj.jus.br/api_publica_tjma/_search",
        "11": "https://api-publica.datajud.cnj.jus.br/api_publica_tjmt/_search",
        "12": "https://api-publica.datajud.cnj.jus.br/api_publica_tjms/_search",
        "13": "https://api-publica.datajud.cnj.jus.br/api_publica_tjmg/_search",
        "14": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpa/_search",
        "15": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpb/_search",
        "16": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpr/_search",
        "17": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpe/_search",
        "18": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpi/_search",
        "19": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search",
        "20": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrn/_search",
        "21": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrs/_search",
        "22": "https://api-publica.datajud.cnj.jus.br/api_publica_tjro/_search",
        "23": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrr/_search",
        "24": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsc/_search",
        "25": "https://api-publica.datajud.cnj.jus.br/api_publica_tjse/_search",
        "26": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
        "27": "https://api-publica.datajud.cnj.jus.br/api_publica_tjto/_search"
    },
    "Justiça do Trabalho": {
        **{str(i): f"https://api-publica.datajud.cnj.jus.br/api_publica_trt{i}/_search" for i in range(1, 25)}
    }
}

# --- FUNÇÕES AUXILIARES ---

def format_date(date_string: Optional[str]) -> str:
    """Tenta formatar uma data do formato ISO para DD/MM/AAAA."""
    if not date_string:
        return ""
    try:
        return datetime.fromisoformat(date_string.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_string # Retorna o original se a formatação falhar

def to_excel(dfs: Dict[str, pd.DataFrame]) -> bytes:
    """Converte um dicionário de DataFrames para um arquivo Excel com múltiplas abas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            # Auto-ajuste da largura das colunas para melhor visualização
            for column in df:
                column_length = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column)
                writer.sheets[sheet_name].set_column(col_idx, col_idx, column_length + 2)
    return output.getvalue()

# --- LÓGICA PRINCIPAL DA APLICAÇÃO ---

def identificar_tribunal(numero_processo_cnj: str, natureza: str) -> Optional[str]:
    """Identifica o endpoint correto do tribunal com base no número do processo CNJ."""
    if natureza == "Justiça do Trabalho":
        match = re.search(r'\.5\.(\d{2})', numero_processo_cnj)
        if match:
            trt_numero = str(int(match.group(1)))
            return ENDPOINTS["Justiça do Trabalho"].get(trt_numero)
    elif natureza == "Justiça Estadual":
        match = re.search(r'\.8\.(\d{2})', numero_processo_cnj)
        if match:
            tj_numero = match.group(1)
            return ENDPOINTS["Justiça Estadual"].get(tj_numero)
    return None

def consultar_processo_datajud(session: requests.Session, numero_processo_cnj: str, natureza: str) -> Optional[Dict[str, Any]]:
    """Realiza a consulta de um único processo na API DataJud."""
    url = identificar_tribunal(numero_processo_cnj, natureza)
    if not url:
        st.warning(f"Não foi possível identificar o tribunal para o processo {numero_processo_cnj}.")
        return None

    headers = {"Authorization": f"APIKey {DATAJUD_API_KEY}", "Content-Type": "application/json"}
    payload = {"query": {"match": {"numeroProcesso": re.sub(r'[\.-]', '', numero_processo_cnj)}}}
    
    try:
        response = session.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro HTTP {e.response.status_code} ao consultar {numero_processo_cnj}. O tribunal pode estar offline.")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão ao consultar o processo {numero_processo_cnj}: {e}")
    return None

def processar_lote_completo(processos: List[str], natureza: str):
    """
    Processa uma lista de processos, extraindo todos os movimentos e identificando
    os possíveis encerramentos, replicando a lógica do script original.
    """
    todos_movimentos = []
    possiveis_encerramentos = []
    
    total_processos = len(processos)
    progress_bar = st.progress(0, text="Iniciando processamento...")
    
    with requests.Session() as session:
        for i, processo_cnj in enumerate(processos):
            progress_text = f"Consultando {i+1}/{total_processos}: {processo_cnj}"
            progress_bar.progress((i + 1) / total_processos, text=progress_text)
            
            resultado_api = consultar_processo_datajud(session, processo_cnj, natureza)
            
            if resultado_api and resultado_api['hits']['total']['value'] > 0:
                for hit in resultado_api['hits']['hits']:
                    dados = hit['_source']
                    data_ajuizamento_formatada = format_date(dados.get('dataAjuizamento'))
                    instancia = dados.get('grau', '')
                    
                    if 'movimentos' in dados and dados['movimentos']:
                        for mov in dados['movimentos']:
                            nome_movimento = mov.get('movimentoNacional', {}).get('descricao') or mov.get('nome', 'N/A')
                            
                            # Lógica para extrair complementos
                            nomes_complementos = 'N/A'
                            if 'complementosTabelados' in mov and mov['complementosTabelados']:
                                nomes_complementos = " - ".join([comp['nome'] for comp in mov['complementosTabelados']])
                            
                            movimento_data = {
                                "Processo": dados.get('numeroProcesso', processo_cnj),
                                "Data Ajuizamento": data_ajuizamento_formatada,
                                "Instância": instancia,
                                "Data Movimento": format_date(mov.get('dataHora')),
                                "Movimentação": nome_movimento,
                                "Complemento": nomes_complementos
                            }
                            todos_movimentos.append(movimento_data)
                            
                            # Lógica para identificar encerramentos (arquivados/definitivos)
                            if re.search(r'definitiv|arquivad|baixado', nome_movimento, re.IGNORECASE):
                                possiveis_encerramentos.append(movimento_data)
                    else:
                        # Processo encontrado mas sem movimentos registrados
                        todos_movimentos.append({
                            "Processo": processo_cnj, "Data Ajuizamento": data_ajuizamento_formatada, "Instância": instancia,
                            "Data Movimento": "", "Movimentação": "Processo sem movimentos registrados na base", "Complemento": ""
                        })
            else:
                # Processo não encontrado na API
                todos_movimentos.append({
                    "Processo": processo_cnj, "Data Ajuizamento": "", "Instância": "", "Data Movimento": "",
                    "Movimentação": "Processo não localizado na base do DataJud", "Complemento": ""
                })

    progress_bar.empty()
    st.session_state.df_resultados = pd.DataFrame(todos_movimentos)
    st.session_state.df_encerramentos = pd.DataFrame(possiveis_encerramentos)

# --- INTERFACE (UI) ---

def tela_login():
    """Exibe a tela de login e gerencia a autenticação."""
    st.title("⚖️ Consultor de Processos Judiciais")
    st.markdown("---")
    with st.form("login_form"):
        password = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if password == APP_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")

def tela_principal():
    """Exibe a interface principal da aplicação após o login."""
    with st.sidebar:
        st.title("⚖️ Consultor")
        st.markdown("---")
        st.write("Bem-vindo(a)!")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("Consulta de Movimentos e Arquivamentos via DataJud/CNJ")
    st.markdown("Faça o upload de uma planilha Excel (`.xlsx`) com uma coluna chamada **'Processo'**.")
    
    controls_container = st.container(border=True)
    with controls_container:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"], label_visibility="collapsed")
        with col2:
            natureza = st.selectbox("Natureza da Justiça", ["Justiça do Trabalho", "Justiça Estadual"])
            
        if uploaded_file:
            if st.button("▶️ Iniciar Processamento", type="primary", use_container_width=True):
                try:
                    df = pd.read_excel(uploaded_file)
                    if "Processo" in df.columns:
                        processos = df['Processo'].astype(str).str.strip().tolist()
                        with st.spinner('Aguarde, consultando processos... Isso pode levar alguns minutos.'):
                            processar_lote_completo(processos, natureza)
                    else:
                        st.error("Erro: A planilha deve conter uma coluna chamada 'Processo'.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo Excel: {e}")

    if 'df_resultados' in st.session_state and not st.session_state.df_resultados.empty:
        st.markdown("---")
        st.subheader("Resultados da Consulta")
        
        df_resultados = st.session_state.df_resultados
        df_encerramentos = st.session_state.df_encerramentos
        
        total_consultado = df_resultados['Processo'].nunique()
        total_encontrado = df_resultados[~df_resultados['Movimentação'].str.contains("não localizado", na=False)]['Processo'].nunique()
        total_arquivados = df_encerramentos['Processo'].nunique()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Processos Consultados", total_consultado)
        col2.metric("Processos Encontrados", total_encontrado)
        col3.metric("Processos com Indicação de Arquivamento", total_arquivados)

        excel_data = to_excel({
            'Todos os Movimentos': df_resultados,
            'Possíveis Encerramentos': df_encerramentos
        })
        st.download_button(
            label="📥 Baixar Relatório Completo em Excel",
            data=excel_data,
            file_name=f"relatorio_processos_{natureza.replace(' ', '_').lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        tab1, tab2 = st.tabs(["📁 Possíveis Encerramentos", "📖 Todos os Movimentos"])
        with tab1:
            st.write(f"Encontrados {len(df_encerramentos)} movimentos que indicam arquivamento ou baixa definitiva.")
            st.dataframe(df_encerramentos, use_container_width=True)
        with tab2:
            st.write(f"Total de {len(df_resultados)} movimentos encontrados para os processos consultados.")
            st.dataframe(df_resultados, use_container_width=True)

# --- INICIALIZAÇÃO E CONTROLE DE FLUXO ---
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        tela_principal()
    else:
        tela_login()

if __name__ == "__main__":
    main()