import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sqlite3
import base64
import os
import zipfile

# Configuração da página para melhor responsividade
st.set_page_config(
    page_title="Livro Caixa",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para melhor responsividade
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stDataFrame {
        font-size: 0.9rem;
    }
    @media (max-width: 768px) {
        .stDataFrame {
            font-size: 0.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Função para carregar e exibir a imagem do logo
def carregar_imagem_logo(caminho_imagem="Logo_Loja.png"):
    """Carrega e exibe a imagem do logo na sidebar"""
    try:
        # Verifica se o arquivo existe
        if os.path.exists(caminho_imagem):
            # Lê a imagem e converte para base64
            with open(caminho_imagem, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode()
            
            # Exibe a imagem na sidebar
            st.sidebar.markdown(
                f"""
                <div style="text-align: center; padding: 10px; margin-bottom: 20px;">
                    <img src="data:image/png;base64,{img_base64}" style="max-width: 100%; height: auto; border-radius: 10px;">
                </div>
                """,
                unsafe_allow_html=True
            )
            return True
        else:
            # Se a imagem não existe, mostra o texto como fallback
            st.sidebar.markdown(
                """
                <div style="text-align: center; padding: 10px; background: linear-gradient(135deg, #1f77b4, #ff7f0e); 
                            border-radius: 10px; margin-bottom: 20px; color: white;">
                    <h2 style="margin-bottom: 5px; font-weight: bold; font-size: 1.2rem;">CONSTITUCIONALISTAS</h2>
                    <h3 style="margin-top: 0; font-weight: bold; font-size: 1rem;">929</h3>
                </div>
                """,
                unsafe_allow_html=True
            )
            return False
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar logo: {str(e)}")
        return False

# Funções para o banco de dados
def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabela para lançamentos
    c.execute('''
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT NOT NULL,
            data DATE NOT NULL,
            historico TEXT NOT NULL,
            complemento TEXT,
            entrada REAL DEFAULT 0,
            saida REAL DEFAULT 0,
            saldo REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela SIMPLIFICADA para contas (sem separação Receitas/Despesas)
    c.execute('''
        CREATE TABLE IF NOT EXISTS contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir contas padrão se a tabela estiver vazia
    c.execute('SELECT COUNT(*) FROM contas')
    if c.fetchone()[0] == 0:
        contas_padrao = [
            'Salários',
            'Aluguel',
            'Energia Elétrica',
            'Água',
            'Telefone',
            'Internet',
            'Material de Expediente',
            'Transporte',
            'Alimentação',
            'Manutenção',
            'Vendas',
            'Serviços Prestados',
            'Consultoria',
            'Outras Receitas',
            'Outras Despesas'
        ]
        for conta in contas_padrao:
            c.execute('INSERT OR IGNORE INTO contas (nome) VALUES (?)', (conta,))
    
    conn.commit()
    conn.close()

def get_lancamentos_mes(mes):
    """Busca lançamentos de um mês específico"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    try:
        df = pd.read_sql(f"SELECT * FROM lancamentos WHERE mes = '{mes}' ORDER BY data, id", conn)
        # Renomear colunas para maiúsculas para compatibilidade
        df.columns = [col.upper() for col in df.columns]
    except Exception as e:
        st.error(f"Erro ao buscar lançamentos: {e}")
        df = pd.DataFrame(columns=['ID', 'MES', 'DATA', 'HISTORICO', 'COMPLEMENTO', 'ENTRADA', 'SAIDA', 'SALDO', 'CREATED_AT'])
    finally:
        conn.close()
    return df

def salvar_lancamento(mes, data, historico, complemento, entrada, saida, saldo):
    """Salva um novo lançamento no banco"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO lancamentos (mes, data, historico, complemento, entrada, saida, saldo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (mes, data, historico, complemento, entrada, saida, saldo))
        conn.commit()
        st.success("✅ Lançamento adicionado com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao salvar lançamento: {e}")
        conn.rollback()
    finally:
        conn.close()

def limpar_lancamentos_mes(mes):
    """Remove todos os lançamentos de um mês"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('DELETE FROM lancamentos WHERE mes = ?', (mes,))
        conn.commit()
        st.success(f"✅ Lançamentos de {mes} removidos com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao limpar lançamentos: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_contas():
    """Busca todas as contas"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    try:
        df = pd.read_sql("SELECT nome FROM contas ORDER BY nome", conn)
        contas = df['nome'].tolist()
    except Exception as e:
        st.error(f"Erro ao buscar contas: {e}")
        contas = []
    finally:
        conn.close()
    return contas

def adicionar_conta(nome_conta):
    """Adiciona uma nova conta"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO contas (nome) VALUES (?)', (nome_conta,))
        conn.commit()
        st.success(f"✅ Conta '{nome_conta}' adicionada com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao adicionar conta: {e}")
        conn.rollback()
    finally:
        conn.close()

# Função para exportar dados em formato CSV
def exportar_para_csv():
    """Exporta dados para formato CSV que pode ser aberto no Excel"""
    try:
        # Criar um arquivo ZIP em memória com múltiplos CSVs
        output = io.BytesIO()
        
        # Criar estrutura de dados para exportação
        dados_exportacao = {}
        
        # Informações do sistema
        dados_exportacao['00_Informacoes.csv'] = pd.DataFrame({
            'Sistema': ['Livro Caixa - CONSTITUCIONALISTAS-929'],
            'Exportado_em': [datetime.now().strftime('%d/%m/%Y %H:%M:%S')],
            'Desenvolvido_por': ['Silmar Tolotto']
        })
        
        # Contas
        contas = get_contas()
        dados_exportacao['01_Contas.csv'] = pd.DataFrame({'Conta': contas})
        
        # Lançamentos por mês
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        for mes in meses:
            df_mes = get_lancamentos_mes(mes)
            if not df_mes.empty:
                # Selecionar e renomear colunas
                colunas_exportar = []
                mapeamento_colunas = {}
                
                if 'DATA' in df_mes.columns:
                    colunas_exportar.append('DATA')
                    mapeamento_colunas['DATA'] = 'Data'
                if 'HISTORICO' in df_mes.columns:
                    colunas_exportar.append('HISTORICO')
                    mapeamento_colunas['HISTORICO'] = 'Histórico'
                if 'COMPLEMENTO' in df_mes.columns:
                    colunas_exportar.append('COMPLEMENTO')
                    mapeamento_colunas['COMPLEMENTO'] = 'Complemento'
                if 'ENTRADA' in df_mes.columns:
                    colunas_exportar.append('ENTRADA')
                    mapeamento_colunas['ENTRADA'] = 'Entrada_R$'
                if 'SAIDA' in df_mes.columns:
                    colunas_exportar.append('SAIDA')
                    mapeamento_colunas['SAIDA'] = 'Saída_R$'
                if 'SALDO' in df_mes.columns:
                    colunas_exportar.append('SALDO')
                    mapeamento_colunas['SALDO'] = 'Saldo_R$'
                
                if colunas_exportar:
                    df_export = df_mes[colunas_exportar].copy()
                    df_export.columns = [mapeamento_colunas[col] for col in colunas_exportar]
                    
                    # Formatar datas
                    if 'Data' in df_export.columns:
                        df_export['Data'] = pd.to_datetime(df_export['Data']).dt.strftime('%d/%m/%Y')
                    
                    dados_exportacao[f'02_{mes}.csv'] = df_export
        
        # Criar um arquivo ZIP com todos os CSVs
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for nome_arquivo, df in dados_exportacao.items():
                csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                zipf.writestr(nome_arquivo, csv_data)
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"❌ Erro ao exportar dados: {e}")
        return None

# Inicializar banco de dados
init_db()

# Sidebar com logo
with st.sidebar:
    # Tenta carregar a imagem do logo
    logo_carregado = carregar_imagem_logo("Logo_Loja.png")
    
    if not logo_carregado:
        st.sidebar.info("💡 Para usar seu logo, coloque o arquivo 'Logo_Loja.png' na mesma pasta do aplicativo")
    
    st.title("📒 Livro Caixa")
    st.markdown("---")
    
    pagina = st.radio(
        "**Navegação:**",
        ["Ajuda", "Contas", "Lançamentos", "Balanço Financeiro", "Exportar Dados"],
        label_visibility="collapsed"
    )

# Página: Ajuda
if pagina == "Ajuda":
    st.title("📋 Ajuda - Livro Caixa")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Sistema Simplificado de Livro Caixa
        
        Este programa serve para lançar todas as receitas e despesas da empresa
        de forma simples e organizada.
        
        **✨ Funcionalidades:**
        - ✅ **Banco de Dados SQLite**: Dados salvos localmente
        - ✅ **Contas Personalizáveis**: Adicione suas próprias contas
        - ✅ **Relatórios**: Balanço financeiro com gráficos
        - ✅ **Exportação**: Backup dos dados em CSV
        
        **📝 Nota:** Não se esqueça do saldo inicial em janeiro!
        """)
        
        st.markdown("---")
        st.subheader("🎯 Como Usar:")
        
        st.markdown("""
        1. **📝 Contas**: Configure suas contas personalizadas
        2. **📥 Lançamentos**: Adicione entradas e saídas por mês
        3. **📈 Balanço**: Veja relatórios e gráficos
        4. **💾 Exportar**: Faça backup dos dados
        """)
    
    with col2:
        st.subheader("💡 Dicas Importantes")
        
        st.markdown("""
        **💰 Movimentações:**
        - **Deposito em banco** → **Saída** do caixa
        - **Retirada do banco** → **Entrada** do caixa
        - **Pagamento** → **Saída** do caixa
        - **Recebimento** → **Entrada** do caixa
        """)

# Página: Contas (SIMPLIFICADA)
elif pagina == "Contas":
    st.title("📝 Contas")
    
    # Buscar contas do banco
    contas = get_contas()
    
    # Lista de contas existentes
    #st.subheader("📋 Contas Cadastradas")
    #if contas:
        #for i, conta in enumerate(contas, 1):
            #st.write(f"{i}. {conta}")
    #else:
        #st.info("📭 Nenhuma conta cadastrada ainda.")
    
    #st.markdown("---")
    
    # Adicionar nova conta
    st.subheader("➕ Adicionar Nova Conta")
    
    nova_conta = st.text_input("**Nome da Nova Conta**", placeholder="Ex: Salários, Aluguel, Vendas...")
    
    if st.button("✅ Adicionar Conta", use_container_width=True) and nova_conta:
        adicionar_conta(nova_conta)
        st.rerun()

# Página: Lançamentos
elif pagina == "Lançamentos":
    st.title("📥 Lançamentos do Caixa")
    
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    # Layout responsivo para seleção de mês
    col1, col2 = st.columns([1, 3])
    
    with col1:
        mes_selecionado = st.selectbox("**Selecione o Mês**", meses)
    
    with col2:
        st.info(f"💼 Trabalhando no mês de **{mes_selecionado}**")
    
    # Buscar lançamentos do banco
    df_mes = get_lancamentos_mes(mes_selecionado)
    
    # Formulário para adicionar lançamento
    st.subheader("➕ Adicionar Lançamento")
    
    # Layout responsivo para o formulário
    with st.form("form_lancamento", clear_on_submit=True):
        col3, col4, col5 = st.columns([2, 2, 1])
        
        with col3:
            data = st.date_input("**Data**", datetime.now().date())
            historico = st.text_input("**Histórico**", placeholder="Descrição do lançamento...")
        
        with col4:
            complemento = st.text_input("**Complemento**", placeholder="Informações adicionais...")
            tipo_movimento = st.selectbox("**Tipo de Movimento**", ["Entrada", "Saída"])
        
        with col5:
            if tipo_movimento == "Entrada":
                entrada = st.number_input("**Valor (R$)**", min_value=0.0, step=0.01, format="%.2f")
                saida = 0.0
            else:
                saida = st.number_input("**Valor (R$)**", min_value=0.0, step=0.01, format="%.2f")
                entrada = 0.0
        
        submitted = st.form_submit_button("💾 Salvar Lançamento", use_container_width=True)
        
        if submitted and historico:
            # Calcular saldo
            if df_mes.empty:
                saldo = entrada - saida
            else:
                # Verifica se a coluna SALDO existe e tem dados
                if 'SALDO' in df_mes.columns and len(df_mes) > 0:
                    saldo_anterior = df_mes.iloc[-1]['SALDO']
                else:
                    saldo_anterior = 0.0
                saldo = saldo_anterior + entrada - saida
            
            # Salvar no banco
            salvar_lancamento(mes_selecionado, data, historico, complemento, entrada, saida, saldo)
            st.rerun()
    
    # Exibir lançamentos do mês
    st.subheader(f"📋 Lançamentos - {mes_selecionado}")
    
    if not df_mes.empty:
        # Mapear colunas do banco para os nomes exibidos
        colunas_mapeadas = {
            'DATA': 'DATA',
            'HISTORICO': 'HISTÓRICO', 
            'COMPLEMENTO': 'COMPLEMENTO',
            'ENTRADA': 'ENTRADA',
            'SAIDA': 'SAÍDA',
            'SALDO': 'SALDO'
        }
        
        # Filtrar apenas colunas que existem no DataFrame
        colunas_existentes = [col for col in colunas_mapeadas.keys() if col in df_mes.columns]
        
        if colunas_existentes:
            df_exibir = df_mes[colunas_existentes].copy()
            
            # Renomear colunas para exibição
            df_exibir.columns = [colunas_mapeadas[col] for col in colunas_existentes]
            
            # Formatar colunas
            if 'DATA' in df_exibir.columns:
                df_exibir['DATA'] = pd.to_datetime(df_exibir['DATA']).dt.strftime('%d/%m/%Y')
            if 'ENTRADA' in df_exibir.columns:
                df_exibir['ENTRADA'] = df_exibir['ENTRADA'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "")
            if 'SAÍDA' in df_exibir.columns:
                df_exibir['SAÍDA'] = df_exibir['SAÍDA'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "")
            if 'SALDO' in df_exibir.columns:
                df_exibir['SALDO'] = df_exibir['SALDO'].apply(lambda x: f"R$ {x:,.2f}")
            
            # Exibir tabela responsiva
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            
            # Estatísticas do mês
            st.subheader("📊 Estatísticas do Mês")
            
            col6, col7, col8 = st.columns(3)
            
            total_entradas = df_mes['ENTRADA'].sum() if 'ENTRADA' in df_mes.columns else 0.0
            total_saidas = df_mes['SAIDA'].sum() if 'SAIDA' in df_mes.columns else 0.0
            
            if 'SALDO' in df_mes.columns and len(df_mes) > 0:
                saldo_atual = df_mes.iloc[-1]['SALDO']
            else:
                saldo_atual = 0.0
            
            with col6:
                st.metric("💰 Total de Entradas", f"R$ {total_entradas:,.2f}")
            with col7:
                st.metric("💸 Total de Saídas", f"R$ {total_saidas:,.2f}")
            with col8:
                st.metric("🏦 Saldo Atual", f"R$ {saldo_atual:,.2f}")
        else:
            st.warning("⚠️ Estrutura de dados incompatível.")
            st.dataframe(df_mes, use_container_width=True)
    else:
        st.info(f"📭 Nenhum lançamento encontrado para {mes_selecionado}")
    
    # Botão para limpar lançamentos do mês
    if st.button(f"🗑️ Limpar Lançamentos de {mes_selecionado}", use_container_width=True, type="secondary"):
        if st.checkbox("✅ Confirmar exclusão"):
            limpar_lancamentos_mes(mes_selecionado)
            st.rerun()

# Página: Balanço Financeiro
elif pagina == "Balanço Financeiro":
    st.title("📈 Balanço Financeiro")
    
    # Calcular totais anuais
    total_entradas_anual = 0.0
    total_saidas_anual = 0.0
    dados_mensais = []
    
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    with st.spinner("📊 Calculando balanço..."):
        for mes in meses:
            df_mes = get_lancamentos_mes(mes)
            if not df_mes.empty:
                entradas_mes = df_mes['ENTRADA'].sum() if 'ENTRADA' in df_mes.columns else 0.0
                saidas_mes = df_mes['SAIDA'].sum() if 'SAIDA' in df_mes.columns else 0.0
                
                if 'SALDO' in df_mes.columns and len(df_mes) > 0:
                    saldo_mes = df_mes.iloc[-1]['SALDO']
                else:
                    saldo_mes = 0.0
                
                total_entradas_anual += entradas_mes
                total_saidas_anual += saidas_mes
                
                dados_mensais.append({
                    'Mês': mes,
                    'Entradas': entradas_mes,
                    'Saídas': saidas_mes,
                    'Saldo': saldo_mes
                })
    
    saldo_final_anual = total_entradas_anual - total_saidas_anual
    
    # Layout responsivo
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Débitos")
        st.metric("**Total de Entradas Anual**", f"R$ {total_entradas_anual:,.2f}")
        
        st.subheader("📅 Resumo por Mês")
        for dados in dados_mensais:
            with st.expander(f"📁 {dados['Mês']}"):
                st.write(f"**Entradas:** R$ {dados['Entradas']:,.2f}")
                st.write(f"**Saídas:** R$ {dados['Saídas']:,.2f}")
                st.write(f"**Saldo:** R$ {dados['Saldo']:,.2f}")
    
    with col2:
        st.subheader("📤 Créditos")
        st.metric("**Total de Saídas Anual**", f"R$ {total_saidas_anual:,.2f}")
        st.metric("**Saldo Final Anual**", f"R$ {saldo_final_anual:,.2f}", 
                 delta=f"R$ {saldo_final_anual:,.2f}")
        
        # Gráfico simples de barras
        if dados_mensais:
            st.subheader("📊 Resumo Visual")
            df_grafico = pd.DataFrame(dados_mensais)
            st.bar_chart(df_grafico.set_index('Mês')[['Entradas', 'Saídas']], use_container_width=True)

# Página: Exportar Dados
elif pagina == "Exportar Dados":
    st.title("💾 Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Exportar Dados")
        
        st.info("💡 Os arquivos CSV podem ser abertos diretamente no Excel")
        
        if st.button("📦 Exportar Todos os Dados", use_container_width=True):
            with st.spinner("Gerando arquivo ZIP..."):
                output = exportar_para_csv()
                
                if output is not None:
                    st.download_button(
                        label="💾 Baixar Arquivo ZIP",
                        data=output,
                        file_name=f"livro_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                    st.success("✅ Arquivo ZIP gerado com sucesso!")
                else:
                    st.error("❌ Erro ao gerar arquivo de exportação")
    
    with col2:
        st.subheader("📊 Informações do Sistema")
        
        # Estatísticas do banco
        conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
        
        try:
            total_lancamentos = pd.read_sql("SELECT COUNT(*) as total FROM lancamentos", conn).iloc[0]['total']
            total_contas = pd.read_sql("SELECT COUNT(*) as total FROM contas", conn).iloc[0]['total']
            meses_com_dados = pd.read_sql("SELECT COUNT(DISTINCT mes) as total FROM lancamentos", conn).iloc[0]['total']
        except:
            total_lancamentos = 0
            total_contas = 0
            meses_com_dados = 0
        
        conn.close()
        
        st.metric("📝 Total de Lançamentos", total_lancamentos)
        st.metric("📋 Total de Contas", total_contas)
        st.metric("📅 Meses com Dados", meses_com_dados)
        
        st.info("""
        **ℹ️ Informações do Sistema:**
        - **Banco de Dados:** SQLite
        - **Arquivo:** `livro_caixa.db`
        - **Dados:** Persistidos localmente
        - **Exportação:** CSV compatível com Excel
        """)

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        <strong>CONSTITUCIONALISTAS-929</strong> - Livro Caixa | 
        Desenvolvido por Silmar Tolotto | 
        {date}
    </div>
    """.format(date=datetime.now().strftime('%d/%m/%Y %H:%M')),
    unsafe_allow_html=True
)
