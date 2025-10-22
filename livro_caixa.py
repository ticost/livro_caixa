import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sqlite3
import base64
from pathlib import Path
import os

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
            ('RECEITAS', 'Lucros na Venda de bens patrimoniais'),
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

def get_plano_contas():
    """Busca o plano de contas"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    try:
        df = pd.read_sql("SELECT tipo, conta FROM plano_contas ORDER BY tipo, conta", conn)
    except Exception as e:
        st.error(f"Erro ao buscar plano de contas: {e}")
        df = pd.DataFrame(columns=['tipo', 'conta'])
    finally:
        conn.close()
    
    # Converter para o formato do dicionário
    plano_contas = {'RECEITAS': [], 'DESPESAS': []}
    for _, row in df.iterrows():
        plano_contas[row['tipo']].append(row['conta'])
    
    return plano_contas

def adicionar_conta_plano(tipo, conta):
    """Adiciona uma nova conta ao plano de contas"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO plano_contas (tipo, conta) VALUES (?, ?)', (tipo, conta))
        conn.commit()
        st.success(f"✅ Conta '{conta}' adicionada com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao adicionar conta: {e}")
        conn.rollback()
    finally:
        conn.close()

# Função para exportar dados sem dependências externas
def exportar_para_excel():
    """Exporta dados para Excel sem usar xlsxwriter"""
    try:
        # Criar um arquivo Excel em memória
        output = io.BytesIO()
        
        # Usar openpyxl como engine (já vem com pandas)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Aba de informações
            info_df = pd.DataFrame({
                'Livro Caixa - CONSTITUCIONALISTAS-929': [
                    f'Exportado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}',
                    'Sistema com Banco de Dados SQLite',
                    'Desenvolvido por Silmar Tolotto'
                ]
            })
            info_df.to_excel(writer, sheet_name='Informações', index=False)
            
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
                    # Selecionar apenas as colunas necessárias
                    colunas_exportar = []
                    if 'DATA' in df_mes.columns:
                        colunas_exportar.append('DATA')
                    if 'HISTORICO' in df_mes.columns:
                        colunas_exportar.append('HISTORICO')
                    if 'COMPLEMENTO' in df_mes.columns:
                        colunas_exportar.append('COMPLEMENTO')
                    if 'ENTRADA' in df_mes.columns:
                        colunas_exportar.append('ENTRADA')
                    if 'SAIDA' in df_mes.columns:
                        colunas_exportar.append('SAIDA')
                    if 'SALDO' in df_mes.columns:
                        colunas_exportar.append('SALDO')
                    
                    if colunas_exportar:
                        df_export = df_mes[colunas_exportar].copy()
                        
                        # Renomear colunas para melhor legibilidade
                        mapeamento_colunas = {
                            'DATA': 'Data',
                            'HISTORICO': 'Histórico',
                            'COMPLEMENTO': 'Complemento',
                            'ENTRADA': 'Entrada (R$)',
                            'SAIDA': 'Saída (R$)',
                            'SALDO': 'Saldo (R$)'
                        }
                        
                        df_export.columns = [mapeamento_colunas.get(col, col) for col in df_export.columns]
                        df_export.to_excel(writer, sheet_name=mes, index=False)
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"❌ Erro ao exportar para Excel: {e}")
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
        ["Ajuda", "Plano de Contas", "Lançamentos", "Balanço Financeiro", "Exportar/Importar"],
        label_visibility="collapsed"
    )

# Página: Ajuda
if pagina == "Ajuda":
    st.title("📋 Ajuda - Livro Caixa")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Versão 2.0 com Banco de Dados
        
        Este programa de livro Caixa servirá para lançar todas as receitas e despesas ocorridas na empresa
        durante todo o ano e diariamente se você preferir.
        
        **✨ Funcionalidades:**
        - ✅ **Banco de Dados SQLite**: Todos os dados são salvos localmente
        - ✅ **Persistência**: Dados mantidos entre execuções
        - ✅ **Relatórios**: Balanço financeiro com gráficos
        - ✅ **Exportação**: Backup dos dados em Excel
        
        **📝 Nota:** Não se esqueça de escrever o saldo do caixa anterior em saldo inicial em janeiro!
        """)
        
        st.markdown("---")
        st.subheader("🎯 Como Usar:")
        
        st.markdown("""
        1. **📥 Lançamentos**: Adicione entradas e saídas por mês
        2. **📊 Plano de Contas**: Gerencie suas categorias
        3. **📈 Balanço**: Veja relatórios e gráficos
        4. **💾 Exportar**: Faça backup dos dados
        """)
    
    with col2:
        st.subheader("💡 Dicas Importantes")
        
        st.markdown("""
        **💰 Movimentações:**
        - **Deposito em banco** → **Saída** do caixa
        - **Retirada do banco** → **Entrada** do caixa
        - **Pagamento de contas** → **Saída** do caixa
        - **Recebimento de valores** → **Entrada** do caixa
        
        **⚡ Atalhos:**
        - Use `Tab` para navegar entre campos
        - `Enter` para confirmar lançamentos
        - Exporte regularmente para backup
        """)

elif pagina == "Plano de Contas":
    st.title("📊 Plano de Contas")
    
    # Buscar plano de contas do banco
    plano_contas = get_plano_contas()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💰 Receitas")
        for conta in plano_contas['RECEITAS']:
            st.write(f"• {conta}")
    
    with col2:
        st.subheader("💸 Despesas")
        for conta in plano_contas['DESPESAS']:
            st.write(f"• {conta}")
    
    st.markdown("---")
    
    # Adicionar nova conta
    st.subheader("➕ Adicionar Nova Conta")
    
    col3, col4 = st.columns([1, 2])
    
    with col3:
        tipo_conta = st.selectbox("**Tipo de Conta**", ["RECEITAS", "DESPESAS"])
    
    with col4:
        nova_conta = st.text_input("**Nome da Nova Conta**", placeholder="Digite o nome da nova conta...")
    
    if st.button("✅ Adicionar Conta", use_container_width=True) and nova_conta:
        adicionar_conta_plano(tipo_conta, nova_conta)
        st.rerun()

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
            st.warning("⚠️ Estrutura de dados incompatível. Mostrando dados brutos:")
            st.dataframe(df_mes, use_container_width=True)
    else:
        st.info(f"📭 Nenhum lançamento encontrado para {mes_selecionado}")
    
    # Botão para limpar lançamentos do mês
    if st.button(f"🗑️ Limpar Todos os Lançamentos de {mes_selecionado}", use_container_width=True, type="secondary"):
        if st.checkbox("✅ Confirmar exclusão de todos os lançamentos deste mês"):
            limpar_lancamentos_mes(mes_selecionado)
            st.rerun()

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

elif pagina == "Exportar/Importar":
    st.title("💾 Exportar/Importar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Exportar Dados")
        
        if st.button("📥 Exportar para Excel", use_container_width=True):
            with st.spinner("Exportando dados para Excel..."):
                output = exportar_para_excel()
                
                if output is not None:
                    st.download_button(
                        label="💾 Baixar Arquivo Excel",
                        data=output,
                        file_name=f"livro_caixa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("❌ Falha ao exportar dados. Verifique se o openpyxl está instalado.")
    
    with col2:
        st.subheader("📊 Informações do Sistema")
        
        # Estatísticas do banco
        conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
        
        try:
            total_lancamentos = pd.read_sql("SELECT COUNT(*) as total FROM lancamentos", conn).iloc[0]['total']
            total_contas = pd.read_sql("SELECT COUNT(*) as total FROM plano_contas", conn).iloc[0]['total']
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
        - **Versão:** 2.0 Corrigida
        """)

# Rodapé atualizado
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        <strong>CONSTITUCIONALISTAS-929</strong> - Livro Caixa | 
        Desenvolvido por Silmar Tolotto em Python | 
        Última atualização: {date}
    </div>
    """.format(date=datetime.now().strftime('%d/%m/%Y %H:%M')),
    unsafe_allow_html=True
)
