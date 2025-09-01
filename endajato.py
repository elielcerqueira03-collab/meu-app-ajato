import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime
import threading
from io import BytesIO

# Dicionário de endpoints para Justiça Estadual (como no seu código original)
ENDPOINTS_JUSTICA_ESTADUAL = {
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
}

# Função de autenticação com senha simples
def autenticar():
    st.sidebar.header("Login")
    senha = st.sidebar.text_input("Digite a senha", type="password")
    if senha == "senha123":
        return True
    else:
        st.sidebar.error("Senha incorreta!")
        return False

# Função para identificar o TRT ou TJ com base no número do processo no formato CNJ
def identificar_justica(numero_processo_cnj, natureza):
    if natureza == "Justiça do Trabalho":
        match = re.search(r'\.5\.(\d{2})', numero_processo_cnj)
        if match:
            trt_numero = match.group(1)
            if trt_numero.startswith("0"):
                trt_numero = trt_numero[1:]  # Remove o zero à esquerda se o TRT for menor que 10
            return f"https://api-publica.datajud.cnj.jus.br/api_publica_trt{trt_numero}/_search"
    elif natureza == "Justiça Estadual":
        match = re.search(r'\.8\.(\d{2})', numero_processo_cnj)
        if match:
            tj_numero = match.group(1)
            return ENDPOINTS_JUSTICA_ESTADUAL.get(tj_numero, None)
    return None

# Função para fazer a consulta no endpoint correto
def consulta_processo(numero_processo_cnj, natureza):
    url = identificar_justica(numero_processo_cnj, natureza)
    if url:
        numero_processo = re.sub(r'[\.-]', '', numero_processo_cnj)  # Remove pontos e traços para a consulta
        headers = {
            "Authorization": "APIKey cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": {
                "match": {
                    "numeroProcesso": numero_processo
                }
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # Levanta um erro se a resposta tiver um código de status de erro
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao consultar o processo {numero_processo_cnj}: {e}")
            return None
    else:
        st.error(f"Não foi possível identificar o endpoint para o processo {numero_processo_cnj}.")
        return None

# Função para processar os dados e exportar para o Excel
def processar_dados(processos, natureza):
    resultados = []  
    possiveis_encerramentos = [] 
    
    for processo in processos:
        resultado = consulta_processo(processo, natureza)
        if resultado and 'hits' in resultado and resultado['hits']['total']['value'] > 0:
            for hit in resultado['hits']['hits']:
                dados_processo = hit['_source']
                instancia = dados_processo.get('grau', '')  

                # Adiciona dados ao resultado
                resultados.append({
                    "Processo": dados_processo.get('numeroProcesso', ''),
                    "Movimentação": dados_processo.get('nomeMovimento', 'N/A'),
                    "Instância": instancia,
                    "Data": dados_processo.get('dataHora', 'N/A'),
                    "Outros Dados": dados_processo.get('outrosCampos', 'N/A')
                })
        else:
            resultados.append({
                "Processo": processo,
                "Movimentação": "Nenhum dado encontrado",
                "Instância": "",
                "Data": "",
                "Outros Dados": ""
            })
    
    df_resultados = pd.DataFrame(resultados)
    st.write(df_resultados)

    # Se quiser exportar os dados para o Excel
    if st.button("Baixar Excel"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_resultados.to_excel(writer, index=False, sheet_name='Resultados')
        st.download_button("Baixar o arquivo", data=output.getvalue(), file_name="resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Interface com Streamlit
def main():
    if not autenticar():
        return

    st.title("Consulta de Processos")

    # Upload do arquivo com os processos
    uploaded_file = st.file_uploader("Selecione o arquivo de entrada", type=["xlsx"])
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        if "Processo" in df.columns:
            processos = df['Processo'].tolist()

            natureza = st.selectbox("Selecione a natureza", ["Justiça do Trabalho", "Justiça Estadual"])
            
            if st.button("Iniciar Processamento"):
                processar_dados(processos, natureza)
        else:
            st.error("A coluna 'Processo' não foi encontrada no arquivo.")

if __name__ == "__main__":
    main()
