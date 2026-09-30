import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import calendar
import unicodedata

# ==========================================
# CONFIGURAÇÃO DA PÁGINA E BANCO DE DADOS
# ==========================================
st.set_page_config(page_title="NutriControl", page_icon="🍽", layout="wide")
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden !important;}
    [data-testid="stHeader"] {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
def get_connection():
    return sqlite3.connect('nutricontrol.db', check_same_thread=False)

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd if not unicodedata.combining(c)]).strip().lower()

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS centros_custo
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cod_erp TEXT, classificacao TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tipos_refeicao
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, peso REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS registros
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, id_cc INTEGER, id_refeicao INTEGER, 
                  categoria TEXT, qtd INTEGER, vol_eq REAL, origem TEXT DEFAULT 'Manual', lote_id TEXT DEFAULT 'Manual')''')
    
    try:
        c.execute("ALTER TABLE registros ADD COLUMN origem TEXT DEFAULT 'Manual'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE registros ADD COLUMN lote_id TEXT DEFAULT 'Manual'")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("UPDATE registros SET origem = 'Importação' WHERE origem = 'Catraca'")
        conn.commit()
    except Exception:
        pass
        
    conn.close()

init_db()

# ==========================================
# MENU LATERAL E LOGO
# ==========================================
st.sidebar.image("Logo_NC.png", use_container_width=True) 
st.sidebar.title("NutriControl")
menu = st.sidebar.radio("Navegação", ["Início", "Lançamento Diário", "Central de Importação", "Cadastros Base", "Painel Gerencial"])

# ==========================================
# MÓDULO 0: TELA INICIAL
# ==========================================
if menu == "Início":
    st.title("Bem-vindo ao NutriControl")
    st.markdown("Sistema de Gestão e Rateio de Custos de Nutrição Hospitalar")
    st.divider()
    
    mes_atual_str = datetime.today().strftime("%Y-%m")
    mes_atual_br = datetime.today().strftime("%B/%Y")
    
    st.subheader(f"Visão Executiva do Mês Atual ({mes_atual_br})")
    
    conn = get_connection()
    query_mes = '''
        SELECT t.nome as Refeicao, r.qtd as Quantidade, r.vol_eq as Volume 
        FROM registros r 
        JOIN tipos_refeicao t ON r.id_refeicao = t.id 
        WHERE substr(r.data, 1, 7) = ?
    '''
    df_mes = pd.read_sql_query(query_mes, conn, params=(mes_atual_str,))
    conn.close()
    
    if df_mes.empty:
        st.info("💡 Nenhum dado registrado para este mês ainda. Utilize o menu lateral para iniciar os lançamentos ou importar arquivos.")
    else:
        total_qtd = df_mes['Quantidade'].sum()
        total_vol = df_mes['Volume'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Total de Refeições Físicas no Mês", f"{total_qtd:,}".replace(",", "."))
        col2.metric("Total de Volume Equivalente (Base)", f"{total_vol:,.1f}".replace(".", ","))
        
        st.divider()
        st.markdown("#### Detalhamento por Tipo de Refeição (Acumulado no Mês)")
        
        df_por_refeicao = df_mes.groupby('Refeicao')['Quantidade'].sum().reset_index()
        cols = st.columns(min(len(df_por_refeicao), 4))
        for index, row in df_por_refeicao.iterrows():
            col = cols[index % len(cols)]
            col.metric(f"Refeição: {row['Refeicao']}", f"{row['Quantidade']:,}".replace(",", "."))
            
    st.divider()
    st.info("💡 Navegue pelo menu lateral para gerenciar as operações, monitorar lotes ou extrair o rateio gerencial.")

# ==========================================
# MÓDULO 2: LANÇAMENTO DIÁRIO, LOTE E AUDITORIA
# ==========================================
elif menu == "Lançamento Diário":
    st.header("Lançamento e Auditoria de Produção")
    
    conn = get_connection()
    ccs = pd.read_sql_query("SELECT id, nome, cod_erp FROM centros_custo", conn)
    refeicoes = pd.read_sql_query("SELECT id, nome, peso FROM tipos_refeicao", conn)
    
    if ccs.empty or refeicoes.empty:
        st.warning("⚠️ Cadastre Centros de Custo e Tipos de Refeição no módulo 'Cadastros Base' primeiro.")
    else:
        tab1, tab2, tab3 = st.tabs(["Lançamento Individual", "⚡ Lançamento em Lote (Rápido)", "📂 Registros Importados"])
        
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
                    
                    conn.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq, origem, lote_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (data_lanc.strftime("%Y-%m-%d"), id_cc, id_ref, categoria, qtd, vol_eq, 'Manual', 'Manual'))
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
                            conn.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq, origem, lote_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (data_lote.strftime("%Y-%m-%d"), id_cc, id_ref, cat_lote, qt, vol_eq, 'Manual', 'Manual'))
                            insercoes += 1
                    
                    if insercoes > 0:
                        conn.commit()
                        st.success(f"Lote gravado: {insercoes} registros realizados.")
                        st.rerun()
                    else:
                        st.warning("Nenhuma quantidade maior que zero informada.")

        with tab3:
            st.markdown("#### Auditoria de Dados Importados (Histórico de Lotes)")
            df_importados = pd.read_sql_query('''
                SELECT r.id, r.lote_id as Lote, r.data as Data_Competencia, c.nome as Setor, t.nome as Refeicao, r.categoria as Categoria, r.qtd as Quantidade 
                FROM registros r JOIN centros_custo c ON r.id_cc = c.id JOIN tipos_refeicao t ON r.id_refeicao = t.id 
                WHERE r.origem = 'Importação' ORDER BY r.id DESC
            ''', conn)
            
            if df_importados.empty:
                st.info("Nenhum dado importado via arquivo até o momento.")
            else:
                df_importados['Data_Competencia'] = pd.to_datetime(df_importados['Data_Competencia']).dt.strftime('%d/%m/%Y')
                st.dataframe(df_importados, hide_index=True, use_container_width=True)
                
                apagar_imp = st.selectbox("Selecionar registro importado para remover:", df_importados.apply(lambda x: f"ID {x['id']} - [Lote: {x['Lote']}] {x['Quantidade']}x {x['Refeicao']} no {x['Setor']}", axis=1).tolist())
                if st.button("🗑️ Excluir Registro Importado Selecionado"):
                    id_imp_del = int(apagar_imp.split(" - ")[0].replace("ID ", ""))
                    conn.execute("DELETE FROM registros WHERE id=?", (id_imp_del,))
                    conn.commit()
                    st.rerun()

        st.divider()
        st.subheader("Auditoria de Lançamentos Manuais do Dia")
        data_auditoria = st.date_input("Escolha a data para verificar/excluir lançamentos manuais:", datetime.today(), format="DD/MM/YYYY")
        df_hoje = pd.read_sql_query('''
            SELECT r.id, c.nome as Setor, t.nome as Refeicao, r.categoria as Categoria, r.qtd as Quantidade, r.vol_eq as Equivalente 
            FROM registros r JOIN centros_custo c ON r.id_cc = c.id JOIN tipos_refeicao t ON r.id_refeicao = t.id 
            WHERE r.data = ? AND r.origem = 'Manual'
        ''', conn, params=(data_auditoria.strftime("%Y-%m-%d"),))
        
        if df_hoje.empty:
            st.info(f"Nenhum lançamento manual registrado em {data_auditoria.strftime('%d/%m/%Y')}.")
        else:
            st.dataframe(df_hoje, hide_index=True, use_container_width=True)
            apagar_reg = st.selectbox("Excluir lançamento manual:", df_hoje.apply(lambda x: f"ID {x['id']} - {x['Quantidade']}x {x['Refeicao']} ({x['Categoria']}) no {x['Setor']}", axis=1).tolist())
            if st.button("🗑 Excluir Manual Selecionado"):
                id_to_delete = int(apagar_reg.split(" - ")[0].replace("ID ", ""))
                conn.execute("DELETE FROM registros WHERE id=?", (id_to_delete,))
                conn.commit()
                st.rerun()
    conn.close()

# ==========================================
# MÓDULO: CENTRAL DE IMPORTAÇÃO
# ==========================================
elif menu == "Central de Importação":
    st.header("Upload e Importação de Dados em Lote")
    
    tab_cc, tab_prod, tab_hist = st.tabs(["🏢 Importar Centros de Custo", "📥 Importar Produção (Lote Geral)", "📋 Histórico de Lotes"])
    
    with tab_cc:
        st.markdown("""
        **Regras para importar Centros de Custo:**
        O arquivo Excel/CSV deve conter exatamente as seguintes colunas na primeira linha:
        `Nome` | `Codigo` | `Classificacao` (Usar: Produtivo, Apoio ou Administrativo).
        """)
        arquivo_cc = st.file_uploader("Selecione o arquivo de Centros de Custo (.csv, .xlsx)", type=['csv', 'xlsx'], key='up_cc')
        
        if arquivo_cc is not None:
            try:
                if arquivo_cc.name.endswith('.csv'):
                    # O sep=None com engine='python' detecta automaticamente se o arquivo usa vírgula, ponto e vírgula ou TAB
                    df_up_cc = pd.read_csv(arquivo_cc, sep=None, engine='python', encoding='latin1', dtype=str)
                else:
                    df_up_cc = pd.read_excel(arquivo_cc, dtype=str)
                    
                st.write("**Pré-visualização dos Centros de Custo a importar:**")
                st.dataframe(df_up_cc.head(20), use_container_width=True)
                
                if st.button("✅ Confirmar e Gravar Centros de Custo"):
                    conn = get_connection()
                    gravados = 0
                    for index, row in df_up_cc.iterrows():
                        codigo_limpo = str(row['Codigo']).strip()
                        existente = conn.execute("SELECT id FROM centros_custo WHERE cod_erp=?", (codigo_limpo,)).fetchone()
                        if not existente:
                            conn.execute("INSERT INTO centros_custo (nome, cod_erp, classificacao) VALUES (?, ?, ?)", 
                                         (str(row['Nome']).strip(), codigo_limpo, str(row['Classificacao']).strip()))
                            gravados += 1
                    conn.commit()
                    conn.close()
                    st.success(f"Centros de custo importados com sucesso! ({gravados} novos registros gravados)")
            except Exception as e:
                st.error(f"Erro ao ler o arquivo. Detalhe: {e}")

    with tab_prod:
        st.markdown("""
        **Regras para importar arquivo de Produção:**
        Use o **Código do Centro de Custo**.
        Colunas obrigatórias: `Codigo_CC` | `Refeicao` | `Categoria` | `Quantidade`.
        """)
        
        mes_prod = st.selectbox("A qual mês esses dados pertencem (Competência Contábil)?", 
                                ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
        ano_prod = st.number_input("Ano da Competência", min_value=2024, max_value=2030, value=datetime.today().year)
        
        arquivo_prod = st.file_uploader("Selecione o arquivo de Produção (.csv, .xlsx)", type=['csv', 'xlsx'], key='up_prod')
        
        if arquivo_prod is not None:
            try:
                if arquivo_prod.name.endswith('.csv'):
                    df_up_prod = pd.read_csv(arquivo_prod, sep=None, engine='python', encoding='latin1', dtype=str)
                else:
                    df_up_prod = pd.read_excel(arquivo_prod, dtype=str)
                    
                st.info(f"Nota: Os dados serão gravados na competência de fechamento de {mes_prod}/{ano_prod}.")
                st.write("**Pré-visualização dos dados a serem importados:**")
                st.dataframe(df_up_prod.head(20), use_container_width=True)
                
                if st.button("✅ Confirmar Gravação da Produção"):
                    conn = get_connection()
                    
                    ccs_cadastrados = pd.read_sql_query("SELECT id, cod_erp FROM centros_custo", conn)
                    ref_cadastradas = pd.read_sql_query("SELECT id, nome, peso FROM tipos_refeicao", conn)
                    
                    dict_cc_cod = dict(zip(ccs_cadastrados.cod_erp.astype(str).str.strip(), ccs_cadastrados.id))
                    
                    dict_ref_normalizado = {}
                    dict_peso = {}
                    for _, r in ref_cadastradas.iterrows():
                        nome_norm = normalizar_texto(r['nome'])
                        dict_ref_normalizado[nome_norm] = r['id']
                        dict_peso[r['id']] = r['peso']
                    
                    mes_num = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"].index(mes_prod) + 1
                    ultimo_dia = calendar.monthrange(ano_prod, mes_num)[1]
                    data_lancamento_prod = f"{ano_prod}-{mes_num:02d}-{ultimo_dia:02d}"
                    
                    lote_id_gerado = f"LOTE_{datetime.today().strftime('%d%m%Y_%H%M%S')}"
                    
                    erros = 0
                    sucessos = 0
                    
                    for index, row in df_up_prod.iterrows():
                        cod_excel = str(row['Codigo_CC']).strip()
                        ref_excel_norm = normalizar_texto(str(row['Refeicao']))
                        
                        if cod_excel in dict_cc_cod and ref_excel_norm in dict_ref_normalizado:
                            id_cc = dict_cc_cod[cod_excel]
                            id_ref = dict_ref_normalizado[ref_excel_norm]
                            qtd = int(float(row['Quantidade'])) 
                            vol_eq = qtd * dict_peso[id_ref]
                            cat = str(row['Categoria']).strip()
                            
                            conn.execute("INSERT INTO registros (data, id_cc, id_refeicao, categoria, qtd, vol_eq, origem, lote_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                      (data_lancamento_prod, id_cc, id_ref, cat, qtd, vol_eq, 'Importação', lote_id_gerado))
                            sucessos += 1
                        else:
                            erros += 1
                            
                    conn.commit()
                    conn.close()
                    
                    if erros > 0:
                        st.warning(f"⚠️ {sucessos} lançamentos importados com sucesso no lote {lote_id_gerado}. {erros} linhas ignoradas (Verifique se o Código do Setor ou o Nome da Refeição conferem exatamente com os Cadastros Base).")
                    else:
                        st.success(f"✅ {sucessos} lançamentos importados com sucesso sob o lote {lote_id_gerado}!")
                        
            except Exception as e:
                st.error(f"Erro na leitura do arquivo. Certifique-se de que os nomes das colunas estão exatos. Detalhe: {e}")

    with tab_hist:
        st.markdown("#### Histórico de Lotes Importados")
        conn = get_connection()
        df_lotes = pd.read_sql_query('''
            SELECT lote_id as Lote, data as Data_Competencia, count(*) as Total_Registros, sum(qtd) as Total_Fisico 
            FROM registros WHERE origem = 'Importação' GROUP BY lote_id, data ORDER BY data DESC
        ''', conn)
        conn.close()
        
        if df_lotes.empty:
            st.info("Nenhum lote importado até o momento.")
        else:
            df_lotes['Data_Competencia'] = pd.to_datetime(df_lotes['Data_Competencia']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_lotes, hide_index=True, use_container_width=True)
            
            lotes_disponiveis = df_lotes['Lote'].tolist()
            lote_para_excluir = st.selectbox("Selecione um lote para exclusão completa (caso tenha subido errado):", lotes_disponiveis)
            
            if st.button("🗑 Excluir Lote Inteiro"):
                conn = get_connection()
                conn.execute("DELETE FROM registros WHERE lote_id = ?", (lote_para_excluir,))
                conn.commit()
                conn.close()
                st.success(f"Lote {lote_para_excluir} removido com sucesso!")
                st.rerun()

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
        df['Data_Original'] = pd.to_datetime(df['Data'])
        min_date = df['Data_Original'].min().date()
        max_date = df['Data_Original'].max().date()
        
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
            
        mask = (df['Data_Original'].dt.date >= data_inicio) & (df['Data_Original'].dt.date <= data_fim) & (df['Tipo'].isin(tipos_selecionados)) & (df['Centro_Custo'].isin(ccs_selecionados))
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
                df_filtrado['Mes_Ano'] = df_filtrado['Data_Original'].dt.strftime('%m/%Y')
                df_comp = df_filtrado.groupby('Mes_Ano')[coluna_valor].sum().reset_index()
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.bar_chart(data=df_comp, x='Mes_Ano', y=coluna_valor, color="#1E293B")
                with c2:
                    df_exibicao_comp = df_comp.rename(columns={'Mes_Ano': 'Mês de Referência', coluna_valor: 'Total Servido'})
                    st.dataframe(df_exibicao_comp, hide_index=True, use_container_width=True)

            st.divider()
            st.subheader("Auditoria de Lançamentos (Base Filtrada)")
            df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data']).dt.strftime('%d/%m/%Y')
            st.dataframe(df_filtrado.drop(columns=['Data_Original', 'Mes_Ano'], errors='ignore'), hide_index=True, use_container_width=True)
