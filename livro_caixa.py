import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sqlite3
import base64
from pathlib import Path
import os

# Configuração da página
st.set_page_config(
    page_title="Livro Caixa",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
                    <h2 style="margin-bottom: 5px; font-weight: bold;">CONSTITUCIONALISTAS</h2>
                    <h3 style="margin-top: 0; font-weight: bold;">929</h3>
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
    conn = sqlite3.connect('livro_caixa.db')
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
    
    # Tabela para plano de contas
    c.execute('''
        CREATE TABLE IF NOT EXISTS plano_contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            conta TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir plano de contas padrão se a tabela estiver vazia
    c.execute('SELECT COUNT(*) FROM plano_contas')
    if c.fetchone()[0] == 0:
        contas_padrao = [
            ('RECEITAS', 'Rendimentos PF não Assalariado'),
            ('RECEITAS', 'Rendimentos PJ não Assalariado'),
            ('RECEITAS', 'Rendimentos PJ Assalariado'),
            ('RECEITAS', 'Receitas de aluguéis'),
            ('RECEITAS', 'Lucros na Venda de bens patrimoniais '),
            ('RECEITAS', 'Rendas Extraordinarias'),
            ('DESPESAS', 'Compras de mercadorias'),
            ('DESPESAS', 'Fretes e Seguros sobre compras'),
            ('DESPESAS', 'Agua e esgoto'),
            ('DESPESAS', 'Energia Elétrica'),
            ('DESPESAS', 'Telefones'),
            ('DESPESAS', 'Provedor - Internet'),
            ('DESPESAS', 'Material de Limpeza'),
            ('DESPESAS', 'Material de Expediente'),
            ('DESPESAS', 'Aluguel'),
            ('DESPESAS', 'Salários'),
            ('DESPESAS', 'INSS'),
            ('DESPESAS', 'IRRF'),
            ('DESPESAS', 'FGTS')
        ]
        c.executemany('INSERT INTO plano_contas (tipo, conta) VALUES (?, ?)', contas_padrao)
    
    conn.commit()
    conn.close()

def get_lancamentos_mes(mes):
    """Busca lançamentos de um mês específico"""
    conn = sqlite3.connect('livro_caixa.db')
    try:
        df = pd.read_sql(f"SELECT * FROM lancamentos WHERE mes = '{mes}' ORDER BY data, id", conn)
    except:
        # Se houver erro, retorna DataFrame vazio com colunas esperadas
        df = pd.DataFrame(columns=['id', 'mes', 'data', 'historico', 'complemento', 'entrada', 'saida', 'saldo', 'created_at'])
    conn.close()
    return df

def salvar_lancamento(mes, data, historico, complemento, entrada, saida, saldo):
    """Salva um novo lançamento no banco"""
    conn = sqlite3.connect('livro_caixa.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO lancamentos (mes, data, historico, complemento, entrada, saida, saldo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (mes, data, historico, complemento, entrada, saida, saldo))
    conn.commit()
    conn.close()

def limpar_lancamentos_mes(mes):
    """Remove todos os lançamentos de um mês"""
    conn = sqlite3.connect('livro_caixa.db')
    c = conn.cursor()
    c.execute('DELETE FROM lancamentos WHERE mes = ?', (mes,))
    conn.commit()
    conn.close()

def get_plano_contas():
    """Busca o plano de contas"""
    conn = sqlite3.connect('livro_caixa.db')
    try:
        df = pd.read_sql("SELECT tipo, conta FROM plano_contas ORDER BY tipo, conta", conn)
    except:
        df = pd.DataFrame(columns=['tipo', 'conta'])
    conn.close()
    
    # Converter para o formato do dicionário
    plano_contas = {'RECEITAS': [], 'DESPESAS': []}
    for _, row in df.iterrows():
        plano_contas[row['tipo']].append(row['conta'])
    
    return plano_contas

def adicionar_conta_plano(tipo, conta):
    """Adiciona uma nova conta ao plano de contas"""
    conn = sqlite3.connect('livro_caixa.db')
    c = conn.cursor()
    c.execute('INSERT INTO plano_contas (tipo, conta) VALUES (?, ?)', (tipo, conta))
    conn.commit()
    conn.close()

# Função para criar DataFrame vazio para um mês
def criar_dataframe_mes():
    return pd.DataFrame({
        'DATA': [datetime.now().date()],
        'HISTÓRICO': [''],
        'COMPLEMENTO': [''],
        'ENTRADA': [0.0],
        'SAIDA': [0.0],
        'SALDO': [0.0]
    })

# Função para calcular saldo
def calcular_saldo(df):
    if df.empty:
        return 0.0
    
    # Verifica se a coluna SALDO existe
    if 'SALDO' not in df.columns:
        df['SALDO'] = 0.0
    
    saldo_anterior = df.iloc[0]['SALDO'] if pd.notna(df.iloc[0]['SALDO']) else 0.0
    
    for i in range(1, len(df)):
        entrada = df.iloc[i]['ENTRADA'] if pd.notna(df.iloc[i]['ENTRADA']) else 0.0
        saida = df.iloc[i]['SAIDA'] if pd.notna(df.iloc[i]['SAIDA']) else 0.0
        saldo_anterior = saldo_anterior + entrada - saida
        df.at[df.index[i], 'SALDO'] = saldo_anterior
    
    return saldo_anterior

# Inicializar banco de dados
init_db()

# Sidebar com logo
with st.sidebar:
    # Tenta carregar a imagem do logo
    logo_carregado = carregar_imagem_logo("Logo_Loja.png")
    
    if not logo_carregado:
        st.sidebar.info("💡 Para usar seu logo, coloque o arquivo 'Logo_Loja.png' na mesma pasta do aplicativo")
    
    st.title("📒 Livro Caixa")
    st.subheader("Navegação")
    
    pagina = st.radio(
        "Selecione a página:",
        ["Ajuda", "Plano de Contas", "Lançamentos", "Balanço Financeiro", "Exportar/Importar"]
    )

# Página: Ajuda
if pagina == "Ajuda":
    st.title("Ajuda - Livro Caixa")
    
    st.markdown("""
    ### Versão 2.0 com Banco de Dados
    
    Este programa de livro Caixa servirá para lançar todas as receitas e despesas ocorridas na empresa
    durante todo o ano e diariamente se você preferir, devendo as receitas e despesas serem lançadas mês a mês.
    
    **✨ Funcionalidades:**
    - **Banco de Dados SQLite**: Todos os dados são salvos localmente
    - **Persistência**: Dados mantidos entre execuções
    - **Relatórios**: Balanço financeiro com gráficos
    - **Exportação**: Backup dos dados em Excel
    
    **Nota:** Não se esqueça de escrever o saldo do caixa anterior em saldo inicial em janeiro!!!!!!
    
    ### Como usar:
    1. **Lançamentos**: Adicione entradas e saídas por mês
    2. **Plano de Contas**: Gerencie suas categorias
    3. **Balanço**: Veja relatórios e gráficos
    4. **Exportar**: Faça backup dos dados
    
    ### DICA IMPORTANTE
    
    - Deposito em banco lançar na **saída** do caixa
    - Retirada do banco lançar na **entrada** do caixa
    - Pagamento de contas lançar na **saída** do caixa
    - Recebimento de valores ou cheques lançar na **entrada** do caixa
    """)

elif pagina == "Plano de Contas":
    st.title("Plano de Contas")
    
    # Buscar plano de contas do banco
    plano_contas = get_plano_contas()
    
    col1, col2 = st.columns(2)
    
    #with col1:
        #st.subheader("Receitas")
        #for conta in plano_contas['RECEITAS']:
            #st.write(f"- {conta}")
    
    #with col2:
        #st.subheader("Despesas")
        #for conta in plano_contas['DESPESAS']:
            #st.write(f"- {conta}")
    
    # Adicionar nova conta
    st.subheader("Adicionar Nova Conta")
    tipo_conta = st.selectbox("Tipo de Conta", ["RECEITAS", "DESPESAS"])
    nova_conta = st.text_input("Nome da Nova Conta")
    
    if st.button("Adicionar Conta") and nova_conta:
        adicionar_conta_plano(tipo_conta, nova_conta)
        st.success(f"Conta '{nova_conta}' adicionada com sucesso!")
        st.rerun()

elif pagina == "Lançamentos":
    st.title("Lançamentos do Caixa")
    
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    mes_selecionado = st.selectbox("Selecione o Mês", meses)
    
    # Buscar lançamentos do banco
    df_mes = get_lancamentos_mes(mes_selecionado)
    
    # Formulário para adicionar lançamento
    st.subheader("Adicionar Lançamento")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data = st.date_input("Data", datetime.now().date())
        historico = st.text_input("Histórico")
    
    with col2:
        complemento = st.text_input("Complemento")
        tipo_movimento = st.selectbox("Tipo de Movimento", ["Entrada", "Saída"])
    
    with col3:
        if tipo_movimento == "Entrada":
            entrada = st.number_input("Valor (Entrada)", min_value=0.0, step=0.01)
            saida = 0.0
        else:
            saida = st.number_input("Valor (Saída)", min_value=0.0, step=0.01)
            entrada = 0.0
    
    if st.button("Adicionar Lançamento") and historico:
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
        st.success("Lançamento adicionado com sucesso!")
        st.rerun()
    
    # Exibir lançamentos do mês
    st.subheader(f"Lançamentos - {mes_selecionado}")
    
    if not df_mes.empty:
        # Verifica se as colunas existem antes de tentar acessá-las
        colunas_necessarias = ['DATA', 'HISTÓRICO', 'COMPLEMENTO', 'ENTRADA', 'SAIDA', 'SALDO']
        colunas_existentes = [col for col in colunas_necessarias if col in df_mes.columns]
        
        if colunas_existentes:
            df_exibir = df_mes[colunas_existentes].copy()
            
            # Formatar colunas se existirem
            if 'DATA' in df_exibir.columns:
                df_exibir['DATA'] = pd.to_datetime(df_exibir['DATA']).dt.strftime('%Y-%m-%d')
            if 'ENTRADA' in df_exibir.columns:
                df_exibir['ENTRADA'] = df_exibir['ENTRADA'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "")
            if 'SAIDA' in df_exibir.columns:
                df_exibir['SAIDA'] = df_exibir['SAIDA'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "")
            if 'SALDO' in df_exibir.columns:
                df_exibir['SALDO'] = df_exibir['SALDO'].apply(lambda x: f"R$ {x:,.2f}")
            
            st.dataframe(df_exibir, use_container_width=True)
            
            # Estatísticas do mês
            col1, col2, col3 = st.columns(3)
            
            total_entradas = df_mes['ENTRADA'].sum() if 'ENTRADA' in df_mes.columns else 0.0
            total_saidas = df_mes['SAIDA'].sum() if 'SAIDA' in df_mes.columns else 0.0
            
            if 'SALDO' in df_mes.columns and len(df_mes) > 0:
                saldo_atual = df_mes.iloc[-1]['SALDO']
            else:
                saldo_atual = 0.0
            
            with col1:
                st.metric("Total de Entradas", f"R$ {total_entradas:,.2f}")
            with col2:
                st.metric("Total de Saídas", f"R$ {total_saidas:,.2f}")
            with col3:
                st.metric("Saldo Atual", f"R$ {saldo_atual:,.2f}")
        else:
            st.warning("Estrutura de dados incompatível. Os lançamentos podem ter sido criados em uma versão anterior.")
            st.dataframe(df_mes, use_container_width=True)
    else:
        st.info(f"Nenhum lançamento encontrado para {mes_selecionado}")
    
    # Botão para limpar lançamentos do mês
    if st.button(f"Limpar Lançamentos de {mes_selecionado}"):
        limpar_lancamentos_mes(mes_selecionado)
        st.success(f"Lançamentos de {mes_selecionado} limpos!")
        st.rerun()

elif pagina == "Balanço Financeiro":
    st.title("Balanço Financeiro")
    
    # Calcular totais anuais
    total_entradas_anual = 0.0
    total_saidas_anual = 0.0
    dados_mensais = []
    
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Débitos")
        st.metric("Total de Entradas Anual", f"R$ {total_entradas_anual:,.2f}")
        
        st.subheader("Resumo por Mês")
        for dados in dados_mensais:
            st.write(f"**{dados['Mês']}:** Entradas: R$ {dados['Entradas']:,.2f} | Saídas: R$ {dados['Saídas']:,.2f} | Saldo: R$ {dados['Saldo']:,.2f}")
    
    with col2:
        st.subheader("Créditos")
        st.metric("Total de Saídas Anual", f"R$ {total_saidas_anual:,.2f}")
        st.metric("Saldo Final Anual", f"R$ {saldo_final_anual:,.2f}")
    
    # Gráfico simples de barras
    if dados_mensais:
        st.subheader("Resumo Visual - Entradas vs Saídas por Mês")
        df_grafico = pd.DataFrame(dados_mensais)
        st.bar_chart(df_grafico.set_index('Mês')[['Entradas', 'Saídas']])

elif pagina == "Exportar/Importar":
    st.title("Exportar/Importar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Exportar Dados")
        
        if st.button("Exportar para Excel"):
            # Criar um arquivo Excel com múltiplas abas
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Aba de ajuda
                ajuda_df = pd.DataFrame({
                    'Ajuda': [
                        'Livro Caixa - CONSTITUCIONALISTAS-929',
                        'Exportado em: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Sistema com Banco de Dados SQLite'
                    ]
                })
                ajuda_df.to_excel(writer, sheet_name='Ajuda', index=False)
                
                # Aba de plano de contas
                plano_contas = get_plano_contas()
                plano_contas_lista = []
                for tipo, contas in plano_contas.items():
                    for conta in contas:
                        plano_contas_lista.append({'Tipo': tipo, 'Conta': conta})
                plano_contas_df = pd.DataFrame(plano_contas_lista)
                plano_contas_df.to_excel(writer, sheet_name='Plano de Contas', index=False)
                
                # Abas para cada mês
                meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                for mes in meses:
                    df_mes = get_lancamentos_mes(mes)
                    if not df_mes.empty:
                        # Verifica colunas antes de exportar
                        colunas_exportar = ['DATA', 'HISTÓRICO', 'COMPLEMENTO', 'ENTRADA', 'SAIDA', 'SALDO']
                        colunas_existentes = [col for col in colunas_exportar if col in df_mes.columns]
                        
                        if colunas_existentes:
                            df_mes[colunas_existentes].to_excel(writer, sheet_name=mes, index=False)
            
            output.seek(0)
            
            st.download_button(
                label="Baixar Arquivo Excel",
                data=output,
                file_name=f"livro_caixa_constituicionalistas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        st.subheader("Informações do Sistema")
        
        # Estatísticas do banco
        conn = sqlite3.connect('livro_caixa.db')
        
        try:
            total_lancamentos = pd.read_sql("SELECT COUNT(*) as total FROM lancamentos", conn).iloc[0]['total']
            total_contas = pd.read_sql("SELECT COUNT(*) as total FROM plano_contas", conn).iloc[0]['total']
            meses_com_dados = pd.read_sql("SELECT COUNT(DISTINCT mes) as total FROM lancamentos", conn).iloc[0]['total']
        except:
            total_lancamentos = 0
            total_contas = 0
            meses_com_dados = 0
        
        conn.close()
        
        st.metric("Total de Lançamentos", total_lancamentos)
        st.metric("Total de Contas no Plano", total_contas)
        st.metric("Meses com Dados", meses_com_dados)
        
        st.info("""
        **Informações do Sistema:**
        - Banco de Dados: SQLite
        - Arquivo: `livro_caixa.db`
        - Dados persistidos localmente
        - Versão: 2.0
        """)

# Rodapé atualizado
st.markdown("---")
st.markdown(
    "**CONSTITUCIONALISTAS-929** - Livro Caixa | "
    "Desenvolvido por Silmar Tolotto em Python | "
    f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}"

)
