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
st.sidebar.image("1000724841.png", use_container_width=True)
st.sidebar.title("Nutri Control")
menu = st.sidebar.radio("Navegação", ["Lançamento Diário", "Cadastros Base", "Dashboard e Exportação"])

# ==========================================
# MÓDULO 2: LANÇAMENTO DIÁRIO E CORREÇÕES
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
                st.rerun()

        st.divider()
        st.subheader(f"Lançamentos registrados para {data_lanc.strftime('%d/%m/%Y')}")
        
        df_hoje = pd.read_sql_query('''
            SELECT r.id, c.nome as Setor, t.nome as Refeicao, r.categoria as Categoria, r.qtd as Quantidade, r.vol_eq as Equivalente 
            FROM registros r 
            JOIN centros_custo c ON r.id_cc = c.id 
            JOIN tipos_refeicao t ON r.id_refeicao = t.id 
            WHERE r.data = ?
        ''', conn, params=(data_lanc.strftime("%Y-%m-%d"),))
        
        if df_hoje.empty:
            st.info("Nenhum lançamento registrado nesta data até o momento.")
        else:
            st.dataframe(df_hoje, hide_index=True, use_container_width=True)
            apagar_reg = st.selectbox("Cometeu um erro? Selecione um lançamento para remover", 
                                      df_hoje.apply(lambda x: f"ID {x['id']} - {x['Quantidade']}x {x['Refeicao']} ({x['Categoria']}) no {x['Setor']}", axis=1).tolist())
            if st.button("🗑️ Excluir Lançamento Errado", key="del_reg"):
                id_to_delete = int(apagar_reg.split(" - ")[0].replace("ID ", ""))
                conn.execute("DELETE FROM registros WHERE id=?", (id_to_delete,))
                conn.commit()
                st.rerun()
                
    conn.close()

# ==========================================
# MÓDULO 1: CADASTROS BASE E VALIDAÇÕES
# ==========================================
elif menu == "Cadastros Base":
    st.header("Gestão de Cadastros")
    
    tab1, tab2 = st.tabs(["🏢 Centros de Custo", "🍽️ Tipos de Refeição"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Novo Cadastro")
            with st.form("form_cc", clear_on_submit=True):
                nome_cc = st.text_input("Nome do Setor (Ex: UTI)")
                cod_erp = st.text_input("Código do Centro de Custo")
                classificacao = st.selectbox("Classificação", ["Produtivo", "Apoio", "Administrativo"])
                
                if st.form_submit_button("Salvar Setor", use_container_width=True):
                    conn = get_connection()
                    existente = conn.execute("SELECT id FROM centros_custo WHERE nome=? OR cod_erp=?", (nome_cc, cod_erp)).fetchone()
                    
                    if existente:
                        st.error("⚠️ Erro: Já existe um Centro de Custo cadastrado com este Nome ou Código.")
                    else:
                        conn.execute("INSERT INTO centros_custo (nome, cod_erp, classificacao) VALUES (?, ?, ?)", (nome_cc, cod_erp, classificacao))
                        conn.commit()
                        st.success("Setor salvo com sucesso!")
                        st.rerun()
                    conn.close()
                    
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
                    existente = conn.execute("SELECT id FROM tipos_refeicao WHERE nome=?", (nome_ref,)).fetchone()
                    
                    if existente:
                        st.error("⚠️ Erro: Já existe uma refeição cadastrada com este nome.")
                    else:
                        conn.execute("INSERT INTO tipos_refeicao (nome, peso) VALUES (?, ?)", (nome_ref, peso_ref))
                        conn.commit()
                        st.success("Refeição salva com sucesso!")
                        st.rerun()
                    conn.close()
                    
        with col2:
            st.subheader("Pesos Definidos")
            conn = get_connection()
            df_ref = pd.read_sql_query("SELECT id, nome as Refeição, peso as Peso FROM tipos_refeicao", conn)
            st.dataframe(df_ref, hide_index=True, use_container_width=True)
            
            if not df_ref.empty:
                apagar_ref = st.selectbox("Selecione uma refeição para remover", df_ref['Refeição'].tolist())
                if st.button("🗑 Deletar Refeição", key="del_ref"):
                    conn.execute("DELETE FROM tipos_refeicao WHERE nome=?", (apagar_ref,))
                    conn.commit()
                    st.rerun()
            conn.close()

# ==========================================
# MÓDULO 3: DASHBOARD DE BI E EXPORTAÇÃO
# ==========================================
elif menu == "Dashboard e Exportação":
    st.header("Controladoria e Inteligência de Dados")
    
    conn = get_connection()
    query = '''
    SELECT r.data as Data, c.nome as Centro_Custo, c.cod_erp as Codigo_CC, t.nome as Tipo, 
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
        # Preparação das Datas para o Filtro
        df['Data'] = pd.to_datetime(df['Data'])
        min_date = df['Data'].min().date()
        max_date = df['Data'].max().date()
        
        # 1. ÁREA DE FILTROS AVANÇADOS
        st.markdown("### Filtros de Análise")
        col_f1, col_f2 = st.columns(2)
        
        with col_f1:
            periodo = st.date_input("Selecione o Período (Início e Fim):", [min_date, max_date], min_value=min_date, max_value=max_date)
            
        with col_f2:
            tipos_disponiveis = df['Tipo'].unique().tolist()
            tipos_selecionados = st.multiselect("Filtrar por Tipos de Refeição:", tipos_disponiveis, default=tipos_disponiveis)
            
        # Trata o retorno do seletor de data (caso o usuário clique apenas no primeiro dia e não no segundo)
        if len(periodo) == 2:
            data_inicio, data_fim = periodo
        else:
            data_inicio = data_fim = periodo[0]
            
        # Aplica os filtros na base de dados (Data e Tipo de Refeição)
        mask = (df['Data'].dt.date >= data_inicio) & (df['Data'].dt.date <= data_fim) & (df['Tipo'].isin(tipos_selecionados))
        df_filtrado = df[mask].copy()
        
        st.divider()
        
        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado para o período e refeições selecionados.")
        else:
            # Controle de Métrica Global (Muda todos os gráficos de uma vez)
            visao = st.radio("Selecione a métrica visual para os relatórios abaixo:", ["Volume Equivalente (Base Ponderada)", "Quantidade Absoluta (Operação)"], horizontal=True)
            coluna_valor = 'Volume_Equivalente' if "Equivalente" in visao else 'Quantidade'
            
            # 2. ABAS ANALÍTICAS (Consolidado vs Comparativo)
            tab1, tab2 = st.tabs(["📊 Visão Consolidada (Fechamento)", "📈 Comparativo Mensal (Tendência)"])
            
            with tab1:
                st.markdown(f"**Rateio do período:** {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
                # Agrupa por Centro de Custo
                df_agrupado = df_filtrado.groupby(['Centro_Custo', 'Codigo_CC'])[coluna_valor].sum().reset_index()
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.bar_chart(data=df_agrupado, x='Centro_Custo', y=coluna_valor, color="#2A9D8F")
                    
                with c2:
                    st.dataframe(df_agrupado, hide_index=True, use_container_width=True)
                    csv = df_agrupado.to_csv(index=False, sep=';', decimal=',')
                    st.download_button("📥 Exportar Rateio (.CSV)", data=csv, file_name='rateio_nutricontrol.csv', mime='text/csv', use_container_width=True)
                    
            with tab2:
                st.markdown("**Evolução de Consumo Mês a Mês** (Baseado no período filtrado acima)")
                
                # Cria uma coluna apenas com "Ano-Mês" para agrupar o gráfico de linhas
                df_filtrado['Mes_Ano'] = df_filtrado['Data'].dt.strftime('%Y-%m')
                df_comp = df_filtrado.groupby('Mes_Ano')[coluna_valor].sum().reset_index()
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.line_chart(data=df_comp, x='Mes_Ano', y=coluna_valor, color="#1E293B")
                
                with c2:
                    # Mostra a tabela lateral renomeando as colunas para ficar bonito
                    df_exibicao_comp = df_comp.rename(columns={'Mes_Ano': 'Mês de Referência', coluna_valor: 'Total Servido'})
                    st.dataframe(df_exibicao_comp, hide_index=True, use_container_width=True)

            # 3. AUDITORIA BRUTA
            st.divider()
            st.subheader("Auditoria de Lançamentos (Base Filtrada)")
            # Converte a data de volta para o formato BR para ficar bonito na tabela
            df_filtrado['Data'] = df_filtrado['Data'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_filtrado.drop(columns=['Mes_Ano'], errors='ignore'), hide_index=True, use_container_width=True)
                
