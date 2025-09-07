import streamlit as st
import pandas as pd
import requests
import re
from io import BytesIO
from typing import List, Dict, Optional, Any
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
# --- ALTERAÇÃO: ATUALIZADO PARA O NOME JUDSCAN ---
st.set_page_config(
    page_title="Judscan",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CREDENCIAIS E CONSTANTES ---
APP_PASSWORD = "senha123"  # <-- Troque esta senha para algo mais seguro
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

def formatar_cnj(numero: str) -> str:
    """Formata um número de processo de 20 dígitos no padrão CNJ."""
    num_limpo = re.sub(r'\D', '', str(numero))
    if len(num_limpo) != 20:
        return numero
    return f"{num_limpo[0:7]}-{num_limpo[7:9]}.{num_limpo[9:13]}.{num_limpo[13:14]}.{num_limpo[14:16]}.{num_limpo[16:20]}"


def format_date(date_string: Optional[str]) -> str:
    """Tenta formatar uma data do formato ISO para DD/MM/AAAA."""
    if not date_string:
        return ""
    try:
        return datetime.fromisoformat(date_string.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_string

def to_excel(dfs: Dict[str, pd.DataFrame]) -> bytes:
    """Converte um dicionário de DataFrames para um arquivo Excel e aplica um estilo ao cabeçalho."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#4F81BD', 'font_color': 'white', 'border': 1
        })

        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1, header=False)
            worksheet = writer.sheets[sheet_name]
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            for i, column in enumerate(df.columns):
                try:
                    column_data_length = df[column].astype(str).map(len).max()
                except (ValueError, TypeError):
                    column_data_length = 0
                column_header_length = len(column)
                column_length = max(column_data_length, column_header_length)
                worksheet.set_column(i, i, column_length + 2)
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
        st.error(f"Erro HTTP {e.response.status_code} ao consultar {numero_processo_cnj}.")
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão ao consultar o processo {numero_processo_cnj}: {e}")
    return None

def processar_lote_completo(processos: List[str], natureza: str):
    """Processa uma lista de processos, extraindo todos os movimentos e identificando possíveis encerramentos."""
    todos_movimentos = []
    possiveis_encerramentos = []
    total_processos = len(processos)
    if total_processos == 0:
        st.warning("Nenhum número de processo foi fornecido.")
        return
    progress_bar = st.progress(0, text="Iniciando processamento...")
    with requests.Session() as session:
        for i, processo_cnj_input in enumerate(processos):
            processo_cnj_formatado = formatar_cnj(processo_cnj_input)
            progress_text = f"Consultando {i+1}/{total_processos}: {processo_cnj_formatado}"
            progress_bar.progress((i + 1) / total_processos, text=progress_text)
            resultado_api = consultar_processo_datajud(session, processo_cnj_formatado, natureza)
            if resultado_api and resultado_api['hits']['total']['value'] > 0:
                for hit in resultado_api['hits']['hits']:
                    dados = hit['_source']
                    data_ajuizamento_formatada = format_date(dados.get('dataAjuizamento'))
                    instancia = dados.get('grau', '')
                    if 'movimentos' in dados and dados['movimentos']:
                        for mov in dados['movimentos']:
                            nome_movimento = mov.get('movimentoNacional', {}).get('descricao') or mov.get('nome', 'N/A')
                            nomes_complementos = 'N/A'
                            if 'complementosTabelados' in mov and mov['complementosTabelados']:
                                nomes_complementos = " - ".join([comp['nome'] for comp in mov['complementosTabelados']])
                            movimento_data = {
                                "Processo (CNJ)": processo_cnj_formatado, "Data Ajuizamento": data_ajuizamento_formatada,
                                "Instância": instancia, "Data Movimento": format_date(mov.get('dataHora')),
                                "Movimentação": nome_movimento, "Complemento": nomes_complementos
                            }
                            todos_movimentos.append(movimento_data)
                            if re.search(r'definitivo|arquivado', nome_movimento, re.IGNORECASE) and not re.search(r'baixa', nome_movimento, re.IGNORECASE):
                                possiveis_encerramentos.append(movimento_data)
                    else:
                        todos_movimentos.append({"Processo (CNJ)": processo_cnj_formatado, "Data Ajuizamento": data_ajuizamento_formatada, "Instância": instancia, "Data Movimento": "", "Movimentação": "Processo sem movimentos registrados na base", "Complemento": ""})
            else:
                todos_movimentos.append({"Processo (CNJ)": processo_cnj_formatado, "Data Ajuizamento": "", "Instância": "", "Data Movimento": "", "Movimentação": "Processo não localizado na base do DataJud", "Complemento": ""})
    progress_bar.empty()
    st.session_state.df_resultados = pd.DataFrame(todos_movimentos)
    st.session_state.df_encerramentos = pd.DataFrame(possiveis_encerramentos)
    st.success("Processamento concluído com sucesso!")


# --- INTERFACE (UI) ---

def tela_login():
    """Exibe a tela de login e gerencia a autenticação."""
    # --- ALTERAÇÃO: ADICIONANDO LOGO E CENTRALIZANDO ---
    try:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("logo.png", use_column_width='auto')
    except Exception:
        # Se a imagem falhar, mostra o título
        st.title("Judscan")
        st.warning("Arquivo 'logo.png' não encontrado. Certifique-se que está na mesma pasta do script.")

    st.subheader("Login de Acesso")
    with st.form("login_form"):
        password = st.text_input("Senha", type="password", key="password_input")
        submitted = st.form_submit_button("Entrar", use_container_width=True)
        if submitted:
            if password == APP_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")

def tela_principal():
    """Exibe a interface principal da aplicação após o login."""
    with st.sidebar:
        # --- ALTERAÇÃO: SUBSTITUINDO TÍTULO PELA LOGO NA SIDEBAR ---
        try:
            st.image("logo.png", use_column_width=True)
        except Exception:
            st.title("Judscan") # Mostra o nome se a imagem falhar
        st.markdown("---")
        st.write("Bem-vindo(a)!")
        if st.button("Sair", use_container_width=True):
            st.session_state.logged_in = False
            for key in st.session_state.keys():
                if key != 'logged_in':
                    del st.session_state[key]
            st.rerun()

    # --- ALTERAÇÃO: ATUALIZANDO TÍTULO PRINCIPAL ---
    st.title("Consulta de Movimentos e Arquivamentos de Processos")
    st.info("Escolha uma opção: faça o upload de uma planilha Excel ou insira os números dos processos manualmente.")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("Selecione a Natureza da Justiça")
        natureza = st.selectbox("Selecione a Natureza da Justiça", ["Justiça do Trabalho", "Justiça Estadual"], key="natureza_justica", label_visibility="collapsed")
    with col2:
        st.markdown("&nbsp;")
        iniciar_processamento = st.button("🚀 Iniciar Processamento", type="primary", use_container_width=True)

    tab_upload, tab_manual = st.tabs(["📤 Upload de Arquivo", "✍️ Digitar Números"])
    processos_para_consultar = []
    with tab_upload:
        st.markdown("A planilha deve ter o formato `.xlsx` e conter uma coluna chamada **'Processo'**.")
        uploaded_file = st.file_uploader("Selecione o arquivo Excel", type=["xlsx"], label_visibility="collapsed")
        if iniciar_processamento and uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                if "Processo" in df.columns:
                    processos_para_consultar = df['Processo'].astype(str).str.strip().tolist()
                else:
                    st.error("Erro: A planilha deve conter uma coluna chamada 'Processo'.")
            except Exception as e:
                st.error(f"Erro ao ler o arquivo Excel: {e}")
    with tab_manual:
        st.markdown("Cole a lista de processos abaixo, um por linha.")
        processos_texto = st.text_area("Números dos Processos", height=200, label_visibility="collapsed", placeholder="0710802-55.2018.8.02.0001\n8000570-84.2023.8.05.0191\n...")
        if iniciar_processamento and processos_texto:
            processos_para_consultar = [p.strip() for p in processos_texto.split('\n') if p.strip()]

    if iniciar_processamento and processos_para_consultar:
        with st.spinner('Aguarde, consultando processos... Isso pode levar alguns minutos.'):
            processar_lote_completo(processos_para_consultar, natureza)

    if 'df_resultados' in st.session_state and not st.session_state.df_resultados.empty:
        st.markdown("---")
        st.subheader("📊 Resultados da Consulta")
        df_resultados = st.session_state.df_resultados
        df_encerramentos = st.session_state.df_encerramentos
        total_consultado = df_resultados['Processo (CNJ)'].nunique()
        total_encontrado = df_resultados[~df_resultados['Movimentação'].str.contains("não localizado", na=False)]['Processo (CNJ)'].nunique()
        total_arquivados = df_encerramentos['Processo (CNJ)'].nunique()
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Processos Consultados", total_consultado)
        col_m2.metric("Processos Encontrados", total_encontrado)
        col_m3.metric("Com Indicação de Arquivamento", total_arquivados)
        excel_data = to_excel({'Possíveis Encerramentos': df_encerramentos})
        st.download_button(
            label="📥 Baixar Relatório de Encerramentos em Excel",
            data=excel_data,
            file_name=f"relatorio_encerramentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        tab_res1, tab_res2 = st.tabs(["📁 Possíveis Encerramentos", "📖 Todos os Movimentos"])
        with tab_res1:
            st.write(f"Encontrados {len(df_encerramentos)} movimentos que indicam arquivamento definitivo.")
            st.dataframe(df_encerramentos, use_container_width=True, height=400)
        with tab_res2:
            st.write(f"Total de {len(df_resultados)} movimentos encontrados para os processos consultados.")
            st.dataframe(df_resultados, use_container_width=True, height=600)

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