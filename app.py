import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="Nutri Control", page_icon="🍽️", layout="wide")

def get_connection():
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
# MENU LATERAL E LOGO
# ==========================================
# Link para um ícone provisório. Você pode substituir a URL abaixo pelo link do seu logotipo real.
st.sidebar.image("1000724841.png", use_container_width=True)
st.sidebar.title("Nutri Control")
menu = st.sidebar.radio("Navegação", ["Lançamento Diário", "Cadastros Base", "Dashboard e Exportação"])

# ==========================================
# MÓDULO 2: LANÇAMENTO DIÁRIO
# ==========================================
if menu == "Lançamento Diário":
    st.header("Lançamento Diário de Refeições")
    
    conn = get_connection()
    ccs = pd.read_sql_query("SELECT id, nome FROM centros_custo", conn)
    refeicoes = pd.read_sql_query("SELECT id, nome, peso FROM tipos_refeicao", conn)
    
    if ccs.empty or refeicoes.empty:
        st.warning("⚠️ Cadastre Centros de Custo e Tipos de Refeição no módulo 'Cadastros Base' antes de iniciar os lançamentos.")
    else:
        with st.form("form_lancamento", clear_on_submit=True):
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                data_lanc = st.date_input("Data", datetime.today())
            with col2:
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
            
            submit = st.form_submit_button("Registrar Produção", use_container_width=True)
            
            if submit:
                id_cc = dict_cc[cc_selecionado]
                id_ref = dict_ref[ref_selecionada]
                peso_ref = dict_peso[id_ref]
                vol_eq = qtd * peso_ref
                
                c = conn.cursor()
                c.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq) VALUES (?, ?, ?, ?, ?, ?)",
                          (data_lanc.strftime("%Y-%m-%d"), id_cc, id_ref, categoria, qtd, vol_eq))
                conn.commit()
                st.success(f"✅ Registrado com sucesso: {qtd}x {ref_selecionada} ({categoria}) para {cc_selecionado}.")
    conn.close()

# ==========================================
# MÓDULO 1: CADASTROS BASE (MELHORADO COM UX)
# ==========================================
elif menu == "Cadastros Base":
    st.header("Gestão de Cadastros")
    
    # Criando abas para melhorar a organização visual
    tab1, tab2 = st.tabs(["🏢 Centros de Custo", "🍽️ Tipos de Refeição"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Novo Cadastro")
            with st.form("form_cc", clear_on_submit=True):
                nome_cc = st.text_input("Nome do Setor (Ex: UTI)")
                cod_erp = st.text_input("Código ERP (TOTVS/MV)")
                classificacao = st.selectbox("Classificação", ["Produtivo", "Apoio", "Administrativo"])
                if st.form_submit_button("Salvar Setor", use_container_width=True):
                    conn = get_connection()
                    conn.execute("INSERT INTO centros_custo (nome, cod_erp, classificacao) VALUES (?, ?, ?)", (nome_cc, cod_erp, classificacao))
                    conn.commit()
                    conn.close()
                    st.rerun()
                    
        with col2:
            st.subheader("Base Cadastrada")
            conn = get_connection()
            df_cc = pd.read_sql_query("SELECT id, nome as Setor, cod_erp as Código, classificacao as Tipo FROM centros_custo", conn)
            st.dataframe(df_cc, hide_index=True, use_container_width=True)
            
            if not df_cc.empty:
                apagar_cc = st.selectbox("Selecione um setor para remover", df_cc['Setor'].tolist())
                if st.button("🗑️ Deletar Setor", key="del_cc"):
                    conn.execute("DELETE FROM centros_custo WHERE nome=?", (apagar_cc,))
                    conn.commit()
                    st.rerun()
            conn.close()

    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Nova Refeição")
            with st.form("form_ref", clear_on_submit=True):
                nome_ref = st.text_input("Nome (Ex: Almoço)")
                peso_ref = st.number_input("Peso (Ex: 1.0)", min_value=0.0, step=0.1)
                if st.form_submit_button("Salvar Refeição", use_container_width=True):
                    conn = get_connection()
                    conn.execute("INSERT INTO tipos_refeicao (nome, peso) VALUES (?, ?)", (nome_ref, peso_ref))
                    conn.commit()
                    conn.close()
                    st.rerun()
                    
        with col2:
            st.subheader("Pesos Definidos")
            conn = get_connection()
            df_ref = pd.read_sql_query("SELECT id, nome as Refeição, peso as Peso FROM tipos_refeicao", conn)
            st.dataframe(df_ref, hide_index=True, use_container_width=True)
            
            if not df_ref.empty:
                apagar_ref = st.selectbox("Selecione uma refeição para remover", df_ref['Refeição'].tolist())
                if st.button("🗑️️ Deletar Refeição", key="del_ref"):
                    conn.execute("DELETE FROM tipos_refeicao WHERE nome=?", (apagar_ref,))
                    conn.commit()
                    st.rerun()
            conn.close()

# ==========================================
# MÓDULO 3: DASHBOARD E EXPORTAÇÃO
# ==========================================
elif menu == "Dashboard e Exportação":
    st.header("Controladoria e Rateio")
    
    conn = get_connection()
    query = '''
    SELECT r.data as Data, c.nome as Centro_Custo, c.cod_erp as ERP, t.nome as Tipo, 
           r.categoria as Categoria, r.qtd as Quantidade, r.vol_eq as Volume_Equivalente
    FROM registros r
    JOIN centros_custo c ON r.id_cc = c.id
    JOIN tipos_refeicao t ON r.id_refeicao = t.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        st.info("Nenhum dado registrado para análise.")
    else:
        visao = st.radio("Selecione a métrica visual:", ["Volume Equivalente (Base Ponderada)", "Quantidade Absoluta (Operação)"], horizontal=True)
        coluna_valor = 'Volume_Equivalente' if "Equivalente" in visao else 'Quantidade'
        
        df_agrupado = df.groupby(['Centro_Custo', 'ERP'])[coluna_valor].sum().reset_index()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.bar_chart(data=df_agrupado, x='Centro_Custo', y=coluna_valor, color="#2A9D8F")
            
        with col2:
            st.dataframe(df_agrupado, hide_index=True, use_container_width=True)
            csv = df_agrupado.to_csv(index=False, sep=';', decimal=',')
            st.download_button("📥 Exportar Rateio (.CSV)", data=csv, file_name='rateio_nutricontrol.csv', mime='text/csv', use_container_width=True)
        
        st.divider()
        st.subheader("Auditoria de Lançamentos")
        st.dataframe(df, hide_index=True, use_container_width=True)
        
