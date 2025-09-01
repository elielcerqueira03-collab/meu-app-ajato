import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
from typing import List, Dict, Optional, Any

# --- CONFIGURAÇÃO DA PÁGINA ---
# st.set_page_config deve ser o primeiro comando Streamlit a ser executado.
st.set_page_config(
    page_title="Consultor de Processos Judiciais",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DICIONÁRIOS DE ENDPOINTS ---
# Unificar os endpoints em um único local para facilitar a manutenção.
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
        # Gerar endpoints para os 24 TRTs dinamicamente para evitar uma lista gigante.
        # Ex: "1": "https://api-publica.datajud.cnj.jus.br/api_publica_trt1/_search"
        **{str(i): f"https://api-publica.datajud.cnj.jus.br/api_publica_trt{i}/_search" for i in range(1, 25)}
    }
}

# --- FUNÇÕES AUXILIARES ---

def to_excel(df: pd.DataFrame) -> bytes:
    """Converte um DataFrame para um arquivo Excel em memória."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados')
        # Opcional: ajustar largura das colunas
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column))
            col_idx = df.columns.get_loc(column)
            writer.sheets['Resultados'].set_column(col_idx, col_idx, column_length)
    processed_data = output.getvalue()
    return processed_data

# --- LÓGICA PRINCIPAL DA APLICAÇÃO ---

def identificar_tribunal(numero_processo_cnj: str, natureza: str) -> Optional[str]:
    """Identifica o endpoint correto do tribunal com base no número do processo CNJ."""
    if natureza == "Justiça do Trabalho":
        match = re.search(r'\.5\.(\d{2})', numero_processo_cnj)
        if match:
            trt_numero = str(int(match.group(1))) # Converte para int e depois str para remover zeros à esquerda (ex: '01' -> '1')
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
        st.warning(f"Não foi possível identificar o tribunal para o processo {numero_processo_cnj}. Verifique o número e a natureza selecionada.")
        return None

    # A chave de API é buscada dos secrets do Streamlit
    api_key = st.secrets.get("DATAJUD_API_KEY")
    if not api_key:
        st.error("Chave de API (DATAJUD_API_KEY) não configurada nos secrets do Streamlit.")
        st.stop()
        
    headers = {
        "Authorization": f"APIKey {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": {
            "match": {
                "numeroProcesso": re.sub(r'[\.-]', '', numero_processo_cnj)
            }
        }
    }
    
    try:
        response = session.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão ao consultar o processo {numero_processo_cnj}: {e}")
        return None

def processar_lote(processos: List[str], natureza: str):
    """Processa uma lista de números de processo e exibe os resultados."""
    if 'resultados' not in st.session_state:
        st.session_state.resultados = []
        
    st.session_state.resultados = []
    total_processos = len(processos)
    progress_bar = st.progress(0, text="Iniciando processamento...")
    
    # Usar uma sessão de requests melhora a performance para múltiplas chamadas
    with requests.Session() as session:
        for i, processo in enumerate(processos):
            # Feedback visual para o usuário
            progress_text = f"Consultando {i+1}/{total_processos}: {processo}"
            progress_bar.progress((i + 1) / total_processos, text=progress_text)
            
            resultado_api = consultar_processo_datajud(session, processo, natureza)
            
            if resultado_api and resultado_api['hits']['total']['value'] > 0:
                for hit in resultado_api['hits']['hits']:
                    dados = hit['_source']
                    movimentos = dados.get('movimentos', [])
                    ultimo_movimento = movimentos[0] if movimentos else {}
                    
                    st.session_state.resultados.append({
                        "Processo": dados.get('numeroProcesso', processo),
                        "Tribunal": dados.get('siglaTribunal', 'N/A'),
                        "Órgão Julgador": dados.get('orgaoJulgador', {}).get('nome', 'N/A'),
                        "Classe": dados.get('classe', {}).get('nome', 'N/A'),
                        "Último Movimento": ultimo_movimento.get('movimentoNacional', {}).get('descricao', 'N/A'),
                        "Data Último Movimento": ultimo_movimento.get('dataHora', 'N/A'),
                    })
            else:
                st.session_state.resultados.append({
                    "Processo": processo,
                    "Tribunal": "Não encontrado", "Órgão Julgador": "N/A", "Classe": "N/A", 
                    "Último Movimento": "Processo não localizado na base do DataJud", "Data Último Movimento": "N/A"
                })

    progress_bar.empty() # Limpa a barra de progresso

# --- INTERFACE (UI) ---

def tela_login():
    """Exibe a tela de login e gerencia a autenticação."""
    st.set_page_config(page_title="Login", layout="centered")
    st.title("⚖️ Consultor de Processos Judiciais")
    st.markdown("---")

    # A senha é buscada dos secrets do Streamlit
    senha_correta = st.secrets.get("APP_PASSWORD")
    if not senha_correta:
        st.error("Senha da aplicação (APP_PASSWORD) não configurada nos secrets.")
        st.stop()

    with st.form("login_form"):
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if password == senha_correta:
                st.session_state.logged_in = True
                st.rerun()  # Recarrega a página para ir para a tela principal
            else:
                st.error("Senha incorreta. Tente novamente.")

def tela_principal():
    """Exibe a interface principal da aplicação após o login."""
    
    # --- Sidebar ---
    with st.sidebar:
        st.title("⚖️ Consultor")
        st.markdown("---")
        st.write("Bem-vindo(a)!")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    # --- Título e Descrição ---
    st.title("Consulta de Processos em Lote via DataJud/CNJ")
    st.markdown("Faça o upload de uma planilha Excel (`.xlsx`) com uma coluna chamada **'Processo'** contendo os números dos processos no formato CNJ.")
    
    # --- Área de Upload e Controles ---
    controls_container = st.container(border=True)
    with controls_container:
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader(
                "Selecione o arquivo Excel", 
                type=["xlsx"],
                label_visibility="collapsed"
            )
        
        with col2:
            natureza = st.selectbox(
                "Natureza da Justiça",
                ["Justiça do Trabalho", "Justiça Estadual"],
                key="natureza_justica"
            )
            
        if uploaded_file is not None:
            if st.button("▶️ Iniciar Processamento", type="primary", use_container_width=True):
                try:
                    df = pd.read_excel(uploaded_file)
                    if "Processo" in df.columns:
                        # Converte para string e remove espaços em branco
                        processos = df['Processo'].astype(str).str.strip().tolist()
                        processar_lote(processos, natureza)
                    else:
                        st.error("Erro: A planilha deve conter uma coluna chamada 'Processo'.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo Excel: {e}")

    # --- Área de Resultados ---
    if 'resultados' in st.session_state and st.session_state.resultados:
        st.markdown("---")
        st.subheader("Resultados da Consulta")
        
        df_resultados = pd.DataFrame(st.session_state.resultados)
        
        # Métricas
        total_consultado = len(df_resultados)
        total_encontrado = len(df_resultados[df_resultados['Tribunal'] != 'Não encontrado'])
        
        col1, col2 = st.columns(2)
        col1.metric("Processos Consultados", total_consultado)
        col2.metric("Processos Encontrados", total_encontrado)

        # Download e Visualização
        st.download_button(
            label="📥 Baixar Resultados em Excel",
            data=to_excel(df_resultados),
            file_name=f"resultados_processos_{natureza.replace(' ', '_').lower()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        with st.expander("Visualizar dados detalhados"):
            st.dataframe(df_resultados)

# --- INICIALIZAÇÃO E CONTROLE DE FLUXO ---
def main():
    # Inicializa o estado de login se não existir
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        tela_principal()
    else:
        tela_login()

if __name__ == "__main__":
    main()