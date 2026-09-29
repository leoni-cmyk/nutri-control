import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Nutri Control", layout="wide")

def get_connection():
    # Cria o banco de dados local chamado nutricontrol.db na mesma pasta
    return sqlite3.connect('nutricontrol.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS centros_custo
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cod_erp TEXT, classificacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tipos_refeicao
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, peso REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS registros
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, id_cc INTEGER, id_refeicao INTEGER, 
                  categoria TEXT, qtd INTEGER, vol_eq REAL)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# MENU LATERAL DE NAVEGAÇÃO
# ==========================================
st.sidebar.title("Nutri Control")
menu = st.sidebar.radio("Módulos", ["Lançamento Diário", "Cadastros Base", "Dashboard e Exportação"])

# ==========================================
# MÓDULO 2: LANÇAMENTO DIÁRIO (Operação)
# ==========================================
if menu == "Lançamento Diário":
    st.header("Lançamento Diário de Refeições")
    
    conn = get_connection()
    ccs = pd.read_sql_query("SELECT id, nome FROM centros_custo", conn)
    refeicoes = pd.read_sql_query("SELECT id, nome, peso FROM tipos_refeicao", conn)
    
    if ccs.empty or refeicoes.empty:
        st.warning("⚠️ Atenção: Cadastre Centros de Custo e Tipos de Refeição no módulo 'Cadastros Base' antes de lançar.")
    else:
        # Formulário de lançamento rápido
        with st.form("form_lancamento", clear_on_submit=True):
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                data_lanc = st.date_input("Data", datetime.today())
            with col2:
                # Dicionário para pegar o ID do CC pelo nome
                dict_cc = dict(zip(ccs.nome, ccs.id))
                cc_selecionado = st.selectbox("Centro de Custo", ccs['nome'].tolist())
            with col3:
                categoria = st.selectbox("Categoria", ["Paciente", "Acompanhante", "Funcionário"])
            with col4:
                dict_ref = dict(zip(refeicoes.nome, refeicoes.id))
                dict_peso = dict(zip(refeicoes.id, refeicoes.peso))
                ref_selecionada = st.selectbox("Tipo de Refeição", refeicoes['nome'].tolist())
            with col5:
                qtd = st.number_input("Quantidade", min_value=1, step=1)
            
            submit = st.form_submit_button("Salvar Lançamento")
            
            if submit:
                id_cc = dict_cc[cc_selecionado]
                id_ref = dict_ref[ref_selecionada]
                peso_ref = dict_peso[id_ref]
                vol_eq = qtd * peso_ref
                
                c = conn.cursor()
                c.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq) VALUES (?, ?, ?, ?, ?, ?)",
                          (data_lanc.strftime("%Y-%m-%d"), id_cc, id_ref, categoria, qtd, vol_eq))
                conn.commit()
                st.success(f"Registrado: {qtd}x {ref_selecionada} ({categoria}) no setor {cc_selecionado}. Volume eq: {vol_eq}")
    conn.close()

# ==========================================
# MÓDULO 1: CADASTROS BASE
# ==========================================
elif menu == "Cadastros Base":
    st.header("Configurações do Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Novo Centro de Custo")
        with st.form("form_cc"):
            nome_cc = st.text_input("Nome do Centro de Custo (Ex: UTI, Refeitório)")
            cod_erp = st.text_input("Código ERP (TOTVS/MV)")
            classificacao = st.selectbox("Classificação", ["Produtivo", "Apoio", "Administrativo"])
            if st.form_submit_button("Salvar Centro de Custo"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("INSERT INTO centros_custo (nome, cod_erp, classificacao) VALUES (?, ?, ?)", (nome_cc, cod_erp, classificacao))
                conn.commit()
                conn.close()
                st.success("Salvo com sucesso!")
                
    with col2:
        st.subheader("Novo Tipo de Refeição")
        with st.form("form_ref"):
            nome_ref = st.text_input("Nome da Refeição (Ex: Almoço, Lanche)")
            peso_ref = st.number_input("Peso para Rateio (Ex: 1.0, 0.3)", min_value=0.0, step=0.1)
            if st.form_submit_button("Salvar Refeição"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("INSERT INTO tipos_refeicao (nome, peso) VALUES (?, ?)", (nome_ref, peso_ref))
                conn.commit()
                conn.close()
                st.success("Salvo com sucesso!")

# ==========================================
# MÓDULO 3: DASHBOARD E EXPORTAÇÃO
# ==========================================
elif menu == "Dashboard e Exportação":
    st.header("Controladoria e Rateio")
    
    conn = get_connection()
    # Puxa os dados cruzando as tabelas
    query = '''
    SELECT r.data, c.nome as centro_custo, c.cod_erp, t.nome as tipo_refeicao, 
           r.categoria, r.qtd, r.vol_eq 
    FROM registros r
    JOIN centros_custo c ON r.id_cc = c.id
    JOIN tipos_refeicao t ON r.id_refeicao = t.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        st.info("Nenhum dado registrado ainda.")
    else:
        visao = st.radio("Escolha a visão:", ["Volume Equivalente (Base de Rateio)", "Quantidade Absoluta (Operacional)"], horizontal=True)
        coluna_valor = 'vol_eq' if "Equivalente" in visao else 'qtd'
        
        # Agrupamento para o gráfico e tabela
        df_agrupado = df.groupby(['centro_custo', 'cod_erp'])[coluna_valor].sum().reset_index()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.bar_chart(data=df_agrupado, x='centro_custo', y=coluna_valor)
            
        with col2:
            st.dataframe(df_agrupado, use_container_width=True)
            
            # Botão de Exportação para Excel/CSV
            csv = df_agrupado.to_csv(index=False, sep=';', decimal=',')
            st.download_button(
                label="📥 Exportar Base para o ERP (CSV)",
                data=csv,
                file_name='base_rateio_nutricontrol.csv',
                mime='text/csv'
            )
