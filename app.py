import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import calendar

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="NutriControl", page_icon="🍽️", layout="wide")

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
    
    # ATUALIZAÇÃO: Força a criação da coluna 'origem' nos bancos de dados antigos que já estavam salvos
    try:
        c.execute("ALTER TABLE registros ADD COLUMN origem TEXT DEFAULT 'Manual'")
    except sqlite3.OperationalError:
        pass # Se a coluna já existir, ele segue o jogo sem dar erro
        
    conn.commit()
    conn.close()

init_db()

# ==========================================
# MENU LATERAL E LOGO (RESTAURADO)
# ==========================================
# Voltamos para a imagem grande na barra lateral
st.sidebar.image("1000724841.png", use_container_width=True) 
st.sidebar.title("NutriControl")
menu = st.sidebar.radio("Navegação", ["Início", "Lançamento Diário", "Central de Importação", "Cadastros Base", "Painel Gerencial"])

# ==========================================
# MÓDULO 0: TELA INICIAL
# ==========================================
if menu == "Início":
    st.title("Bem-vindo ao NutriControl")
    st.markdown("Sistema de Gestão e Rateio de Custos de Nutrição Hospitalar")
    st.divider()
    
    hoje_str = datetime.today().strftime("%Y-%m-%d")
    hoje_br = datetime.today().strftime("%d/%m/%Y")
    
    st.subheader(f"Visão Operacional - Hoje ({hoje_br})")
    
    conn = get_connection()
    df_hoje = pd.read_sql_query("SELECT qtd, vol_eq FROM registros WHERE data = ?", conn, params=(hoje_str,))
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    if df_hoje.empty:
        col1.metric("Refeições Físicas Servidas", "0")
        col2.metric("Volume Equivalente (Base)", "0.0")
        col3.metric("Lançamentos Registrados", "0")
    else:
        total_qtd = df_hoje['qtd'].sum()
        total_vol = df_hoje['vol_eq'].sum()
        col1.metric("Refeições Físicas Servidas", f"{total_qtd:,}".replace(",", "."))
        col2.metric("Volume Equivalente (Base)", f"{total_vol:,.1f}".replace(".", ","))
        col3.metric("Lançamentos Registrados", str(len(df_hoje)))
        
    st.info("💡 Navegue pelo menu lateral para gerenciar as operações ou acessar os relatórios gerenciais.")

# ==========================================
# MÓDULO 2: LANÇAMENTO DIÁRIO E LOTE
# ==========================================
elif menu == "Lançamento Diário":
    st.header("Lançamento Diário de Refeições")
    
    conn = get_connection()
    ccs = pd.read_sql_query("SELECT id, nome, cod_erp FROM centros_custo", conn)
    refeicoes = pd.read_sql_query("SELECT id, nome, peso FROM tipos_refeicao", conn)
    
    if ccs.empty or refeicoes.empty:
        st.warning("⚠️ Cadastre Centros de Custo e Tipos de Refeição no módulo 'Cadastros Base' primeiro.")
    else:
        tab1, tab2 = st.tabs(["Lançamento Individual", "⚡ Lançamento em Lote (Rápido)"])
        
        with tab1:
            with st.form("form_lancamento", clear_on_submit=True):
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    data_lanc = st.date_input("Data", datetime.today(), format="DD/MM/YYYY")
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
                
                if st.form_submit_button("Registrar Produção", use_container_width=True):
                    id_cc = dict_cc[cc_selecionado]
                    id_ref = dict_ref[ref_selecionada]
                    vol_eq = qtd * dict_peso[id_ref]
                    
                    conn.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq, origem) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (data_lanc.strftime("%Y-%m-%d"), id_cc, id_ref, categoria, qtd, vol_eq, 'Manual'))
                    conn.commit()
                    st.success("Lançamento efetuado com sucesso!")
                    st.rerun()

        with tab2:
            with st.form("form_lote", clear_on_submit=True):
                st.markdown("**1. Selecione o Destino:**")
                cL1, cL2, cL3 = st.columns(3)
                with cL1:
                    data_lote = st.date_input("Data da Produção", datetime.today(), format="DD/MM/YYYY", key="dlote")
                with cL2:
                    cc_lote = st.selectbox("Centro de Custo", ccs['nome'].tolist(), key="cclote")
                with cL3:
                    cat_lote = st.selectbox("Categoria", ["Paciente", "Acompanhante", "Funcionário"], key="catlote")
                
                st.markdown("**2. Informe as Quantidades:**")
                cols_refeicoes = st.columns(4) 
                qtd_lote_inputs = {}
                dict_peso = dict(zip(refeicoes.id, refeicoes.peso))
                
                for index, row in refeicoes.iterrows():
                    col = cols_refeicoes[index % 4]
                    qtd_lote_inputs[row['id']] = col.number_input(row['nome'], min_value=0, step=1, key=f"ref_{row['id']}")
                
                if st.form_submit_button("Gravar Lote Completo", use_container_width=True):
                    id_cc = dict_cc[cc_lote]
                    insercoes = 0
                    for id_ref, qt in qtd_lote_inputs.items():
                        if qt > 0:
                            vol_eq = qt * dict_peso[id_ref]
                            conn.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq, origem) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                      (data_lote.strftime("%Y-%m-%d"), id_cc, id_ref, cat_lote, qt, vol_eq, 'Manual'))
                            insercoes += 1
                    
                    if insercoes > 0:
                        conn.commit()
                        st.success(f"Lote gravado: {insercoes} registros realizados.")
                        st.rerun()
                    else:
                        st.warning("Nenhuma quantidade maior que zero informada.")

        st.divider()
        st.subheader("Auditoria do Dia")
        data_auditoria = st.date_input("Escolha a data para verificar/excluir lançamentos:", datetime.today(), format="DD/MM/YYYY")
        df_hoje = pd.read_sql_query('''
            SELECT r.id, c.nome as Setor, t.nome as Refeicao, r.categoria as Categoria, r.qtd as Quantidade, r.vol_eq as Equivalente, r.origem as Origem 
            FROM registros r JOIN centros_custo c ON r.id_cc = c.id JOIN tipos_refeicao t ON r.id_refeicao = t.id 
            WHERE r.data = ?
        ''', conn, params=(data_auditoria.strftime("%Y-%m-%d"),))
        
        if not df_hoje.empty:
            st.dataframe(df_hoje, hide_index=True, use_container_width=True)
            apagar_reg = st.selectbox("Excluir lançamento:", df_hoje.apply(lambda x: f"ID {x['id']} - {x['Quantidade']}x {x['Refeicao']} ({x['Categoria']}) no {x['Setor']} [{x['Origem']}]", axis=1).tolist())
            if st.button("🗑 Excluir Selecionado"):
                id_to_delete = int(apagar_reg.split(" - ")[0].replace("ID ", ""))
                conn.execute("DELETE FROM registros WHERE id=?", (id_to_delete,))
                conn.commit()
                st.rerun()
    conn.close()

# ==========================================
# MÓDULO NOVO: CENTRAL DE IMPORTAÇÃO
# ==========================================
elif menu == "Central de Importação":
    st.header("Upload e Importação de Dados em Lote")
    
    tab_cc, tab_prod = st.tabs(["🏢 Importar Centros de Custo", "🏭 Importar Produção (Catraca)"])
    
    with tab_cc:
        st.markdown("""
        **Regras para importar Centros de Custo:**
        O arquivo Excel/CSV deve conter exatamente as seguintes colunas na primeira linha:
        `Nome` | `Codigo` | `Classificacao` (Usar: Produtivo, Apoio ou Administrativo).
        """)
        arquivo_cc = st.file_uploader("Selecione o arquivo de Centros de Custo (.csv, .xlsx)", type=['csv', 'xlsx'], key='up_cc')
        
        if arquivo_cc is not None:
            try:
                df_up_cc = pd.read_csv(arquivo_cc, sep=';') if arquivo_cc.name.endswith('.csv') else pd.read_excel(arquivo_cc)
                st.dataframe(df_up_cc.head(), use_container_width=True)
                
                if st.button("✅ Confirmar e Gravar Centros de Custo"):
                    conn = get_connection()
                    for index, row in df_up_cc.iterrows():
                        existente = conn.execute("SELECT id FROM centros_custo WHERE cod_erp=?", (str(row['Codigo']),)).fetchone()
                        if not existente:
                            conn.execute("INSERT INTO centros_custo (nome, cod_erp, classificacao) VALUES (?, ?, ?)", 
                                         (str(row['Nome']), str(row['Codigo']), str(row['Classificacao'])))
                    conn.commit()
                    conn.close()
                    st.success("Centros de custo importados com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler o arquivo. Verifique se o formato está correto. Detalhe: {e}")

    with tab_prod:
        st.markdown("""
        **Regras para importar arquivo da Catraca:**
        Use o **Código do Centro de Custo**.
        Colunas obrigatórias: `Codigo_CC` | `Refeicao` | `Categoria` | `Quantidade`.
        """)
        
        mes_catraca = st.selectbox("A qual mês esses dados da catraca pertencem?", 
                                   ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        ano_catraca = st.number_input("Ano da Competência", min_value=2024, max_value=2030, value=datetime.today().year)
        
        arquivo_prod = st.file_uploader("Selecione o arquivo da Catraca (.csv, .xlsx)", type=['csv', 'xlsx'], key='up_prod')
        
        if arquivo_prod is not None:
            try:
                df_up_prod = pd.read_csv(arquivo_prod, sep=';') if arquivo_prod.name.endswith('.csv') else pd.read_excel(arquivo_prod)
                st.info(f"O sistema gravará estes dados com a data de fechamento: Final de {mes_catraca}/{ano_catraca}.")
                
                st.write("**Pré-visualização dos dados a serem importados:**")
                st.dataframe(df_up_prod.head(10), use_container_width=True)
                
                if st.button("✅ Confirmar Gravação da Produção"):
                    conn = get_connection()
                    
                    ccs_cadastrados = pd.read_sql_query("SELECT id, cod_erp FROM centros_custo", conn)
                    ref_cadastradas = pd.read_sql_query("SELECT id, nome, peso FROM tipos_refeicao", conn)
                    
                    dict_cc_cod = dict(zip(ccs_cadastrados.cod_erp.astype(str), ccs_cadastrados.id))
                    dict_ref_nome = dict(zip(ref_cadastradas.nome.str.lower(), ref_cadastradas.id))
                    dict_peso = dict(zip(ref_cadastradas.id, ref_cadastradas.peso))
                    
                    mes_num = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"].index(mes_catraca) + 1
                    ultimo_dia = calendar.monthrange(ano_catraca, mes_num)[1]
                    data_lancamento_catraca = f"{ano_catraca}-{mes_num:02d}-{ultimo_dia:02d}"
                    
                    erros = 0
                    sucessos = 0
                    
                    for index, row in df_up_prod.iterrows():
                        cod_excel = str(row['Codigo_CC']).strip()
                        ref_excel = str(row['Refeicao']).strip().lower()
                        
                        if cod_excel in dict_cc_cod and ref_excel in dict_ref_nome:
                            id_cc = dict_cc_cod[cod_excel]
                            id_ref = dict_ref_nome[ref_excel]
                            qtd = int(row['Quantidade'])
                            vol_eq = qtd * dict_peso[id_ref]
                            cat = str(row['Categoria'])
                            
                            conn.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq, origem) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                      (data_lancamento_catraca, id_cc, id_ref, cat, qtd, vol_eq, 'Catraca'))
                            sucessos += 1
                        else:
                            erros += 1
                            
                    conn.commit()
                    conn.close()
                    
                    if erros > 0:
                        st.warning(f"{sucessos} lançamentos importados. {erros} linhas ignoradas (Código do Setor ou Nome da Refeição não encontrados no sistema).")
                    else:
                        st.success(f"{sucessos} lançamentos importados com sucesso!")
                        
            except Exception as e:
                st.error(f"Erro na leitura do arquivo. Certifique-se de que os nomes das colunas estão exatos. {e}")

# ==========================================
# MÓDULO 1: CADASTROS BASE
# ==========================================
elif menu == "Cadastros Base":
    st.header("Gestão de Cadastros")
    tab1, tab2 = st.tabs(["🏢 Centros de Custo", "🍽️ Tipos de Refeição"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            with st.form("form_cc", clear_on_submit=True):
                nome_cc = st.text_input("Nome do Setor")
                cod_erp = st.text_input("Código do Centro de Custo")
                classificacao = st.selectbox("Classificação", ["Produtivo", "Apoio", "Administrativo"])
                
                if st.form_submit_button("Salvar Setor", use_container_width=True):
                    conn = get_connection()
                    existente = conn.execute("SELECT id FROM centros_custo WHERE nome=? OR cod_erp=?", (nome_cc, cod_erp)).fetchone()
                    if existente:
                        st.error("⚠️ Já existe um Centro de Custo com este Nome ou Código.")
                    else:
                        conn.execute("INSERT INTO centros_custo (nome, cod_erp, classificacao) VALUES (?, ?, ?)", (nome_cc, cod_erp, classificacao))
                        conn.commit()
                        st.success("Salvo!")
                        st.rerun()
                    conn.close()
                    
        with col2:
            conn = get_connection()
            df_cc = pd.read_sql_query("SELECT id, nome as Setor, cod_erp as Código, classificacao as Tipo FROM centros_custo", conn)
            st.dataframe(df_cc, hide_index=True, use_container_width=True)
            if not df_cc.empty:
                apagar_cc = st.selectbox("Remover Setor:", df_cc['Setor'].tolist())
                if st.button("🗑️ Deletar"):
                    conn.execute("DELETE FROM centros_custo WHERE nome=?", (apagar_cc,))
                    conn.commit()
                    st.rerun()
            conn.close()

    with tab2:
        col1, col2 = st.columns([1, 2])
        with col1:
            with st.form("form_ref", clear_on_submit=True):
                nome_ref = st.text_input("Nome da Refeição")
                peso_ref = st.number_input("Peso de Rateio", min_value=0.0, step=0.1)
                if st.form_submit_button("Salvar", use_container_width=True):
                    conn = get_connection()
                    existente = conn.execute("SELECT id FROM tipos_refeicao WHERE nome=?", (nome_ref,)).fetchone()
                    if existente:
                        st.error("⚠️ Esta refeição já existe.")
                    else:
                        conn.execute("INSERT INTO tipos_refeicao (nome, peso) VALUES (?, ?)", (nome_ref, peso_ref))
                        conn.commit()
                        st.success("Salvo!")
                        st.rerun()
                    conn.close()
                    
        with col2:
            conn = get_connection()
            df_ref = pd.read_sql_query("SELECT id, nome as Refeição, peso as Peso FROM tipos_refeicao", conn)
            st.dataframe(df_ref, hide_index=True, use_container_width=True)
            if not df_ref.empty:
                apagar_ref = st.selectbox("Remover Refeição:", df_ref['Refeição'].tolist())
                if st.button("🗑 Deletar"):
                    conn.execute("DELETE FROM tipos_refeicao WHERE nome=?", (apagar_ref,))
                    conn.commit()
                    st.rerun()
            conn.close()

# ==========================================
# MÓDULO 3: PAINEL GERENCIAL E EXPORTAÇÃO
# ==========================================
elif menu == "Painel Gerencial":
    st.header("Painel Gerencial e Consolidação de Dados")
    
    conn = get_connection()
    query = '''
    SELECT r.data as Data, c.nome as Centro_Custo, c.cod_erp as Codigo_CC, t.nome as Tipo, 
           r.categoria as Categoria, r.qtd as Quantidade, r.vol_eq as Volume_Equivalente, r.origem as Origem
    FROM registros r JOIN centros_custo c ON r.id_cc = c.id JOIN tipos_refeicao t ON r.id_refeicao = t.id
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        st.info("Nenhum dado registrado para análise.")
    else:
        df['Data'] = pd.to_datetime(df['Data'])
        min_date = df['Data'].min().date()
        max_date = df['Data'].max().date()
        
        st.markdown("### Filtros de Análise")
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            periodo = st.date_input("Período (Início e Fim):", [min_date, max_date], min_value=min_date, max_value=max_date, format="DD/MM/YYYY")
        with col_f2:
            tipos_disponiveis = df['Tipo'].unique().tolist()
            tipos_selecionados = st.multiselect("Tipos de Refeição:", tipos_disponiveis, default=tipos_disponiveis)
        with col_f3:
            ccs_disponiveis = df['Centro_Custo'].unique().tolist()
            ccs_selecionados = st.multiselect("Centros de Custo:", ccs_disponiveis, default=ccs_disponiveis)
            
        if len(periodo) == 2:
            data_inicio, data_fim = periodo
        else:
            data_inicio = data_fim = periodo[0]
            
        mask = (df['Data'].dt.date >= data_inicio) & (df['Data'].dt.date <= data_fim) & (df['Tipo'].isin(tipos_selecionados)) & (df['Centro_Custo'].isin(ccs_selecionados))
        df_filtrado = df[mask].copy()
        
        st.divider()
        
        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado com os filtros selecionados.")
        else:
            visao = st.radio("Métrica Visual:", ["Volume Equivalente (Base Ponderada)", "Quantidade Absoluta (Operação)"], horizontal=True)
            coluna_valor = 'Volume_Equivalente' if "Equivalente" in visao else 'Quantidade'
            
            tab1, tab2 = st.tabs(["📊 Visão por Refeições e Rateio", "📈 Comparativo Mensal (Tendência)"])
            
            with tab1:
                st.markdown(f"**Consolidação do período:** {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
                
                st.markdown("#### Volume por Tipo de Refeição")
                df_chart_refeicao = df_filtrado.groupby('Tipo')[coluna_valor].sum().reset_index()
                st.bar_chart(data=df_chart_refeicao, x='Tipo', y=coluna_valor, color='Tipo')
                
                st.markdown("#### Base de Rateio por Centro de Custo")
                df_agrupado_tipo = df_filtrado.groupby(['Centro_Custo', 'Codigo_CC', 'Tipo'])[coluna_valor].sum().reset_index()
                df_pivot = df_agrupado_tipo.pivot_table(index=['Centro_Custo', 'Codigo_CC'], columns='Tipo', values=coluna_valor, aggfunc='sum', fill_value=0).reset_index()
                
                colunas_refeicoes = [col for col in df_pivot.columns if col not in ['Centro_Custo', 'Codigo_CC']]
                df_pivot['Total_Setor'] = df_pivot[colunas_refeicoes].sum(axis=1)
                
                st.dataframe(df_pivot, hide_index=True, use_container_width=True)
                csv = df_pivot.to_csv(index=False, sep=';', decimal=',')
                st.download_button("📥 Exportar Matriz de Rateio (.CSV)", data=csv, file_name='rateio_detalhado_NutriControl.csv', mime='text/csv', use_container_width=True)
                    
            with tab2:
                st.markdown("**Comparativo de Consumo Mês a Mês** (Barras Consolidadas)")
                df_filtrado['Mes_Ano'] = df_filtrado['Data'].dt.strftime('%m/%Y')
                df_comp = df_filtrado.groupby('Mes_Ano')[coluna_valor].sum().reset_index()
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.bar_chart(data=df_comp, x='Mes_Ano', y=coluna_valor, color="#1E293B")
                with c2:
                    df_exibicao_comp = df_comp.rename(columns={'Mes_Ano': 'Mês de Referência', coluna_valor: 'Total Servido'})
                    st.dataframe(df_exibicao_comp, hide_index=True, use_container_width=True)

            st.divider()
            st.subheader("Auditoria de Lançamentos (Base Filtrada)")
            df_filtrado['Data'] = df_filtrado['Data'].dt.strftime('%d/%m/%Y')
            st.dataframe(df_filtrado.drop(columns=['Mes_Ano'], errors='ignore'), hide_index=True, use_container_width=True)
