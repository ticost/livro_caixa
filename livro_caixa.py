import streamlit as st
import pandas as pd
from datetime import datetime
import io
import sqlite3
import base64
import os
import zipfile
import hashlib

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

# Funções de autenticação
def init_auth_db():
    """Inicializa a tabela de usuários"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inserir usuário padrão se não existir
    c.execute('SELECT COUNT(*) FROM usuarios WHERE username = ?', ('admin',))
    if c.fetchone()[0] == 0:
        # Senha padrão: "admin123"
        password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute('INSERT INTO usuarios (username, password_hash) VALUES (?, ?)', 
                 ('admin', password_hash))
    
    conn.commit()
    conn.close()

def verify_password(password, password_hash):
    """Verifica se a senha está correta"""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash

def login_user(username, password):
    """Faz login do usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('SELECT password_hash FROM usuarios WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if result and verify_password(password, result[0]):
        st.session_state.logged_in = True
        st.session_state.username = username
        return True
    return False

def logout_user():
    """Faz logout do usuário"""
    st.session_state.logged_in = False
    st.session_state.username = None

def change_password(username, new_password):
    """Altera a senha do usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    c.execute('UPDATE usuarios SET password_hash = ? WHERE username = ?', 
             (password_hash, username))
    conn.commit()
    conn.close()

def create_user(username, password):
    """Cria um novo usuário"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        c.execute('INSERT INTO usuarios (username, password_hash) VALUES (?, ?)', 
                 (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Usuário já existe
    except Exception as e:
        return False
    finally:
        conn.close()

def get_all_users():
    """Busca todos os usuários (apenas para admin)"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute('SELECT username, created_at FROM usuarios ORDER BY created_at')
    users = c.fetchall()
    conn.close()
    
    return users

def delete_user(username):
    """Exclui um usuário (apenas para admin)"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    
    try:
        # Não permitir excluir o próprio usuário
        if username == st.session_state.username:
            return False, "Não é possível excluir seu próprio usuário!"
        
        c.execute('DELETE FROM usuarios WHERE username = ?', (username,))
        conn.commit()
        return True, "Usuário excluído com sucesso!"
    except Exception as e:
        return False, f"Erro ao excluir usuário: {e}"
    finally:
        conn.close()

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

def atualizar_lancamento(lancamento_id, mes, data, historico, complemento, entrada, saida):
    """Atualiza um lançamento existente no banco"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    try:
        # Buscar todos os lançamentos do mês para recalcular saldos
        c.execute('SELECT * FROM lancamentos WHERE mes = ? ORDER BY data, id', (mes,))
        lancamentos = c.fetchall()
        
        # Encontrar o índice do lançamento sendo editado
        index_editado = None
        for i, lanc in enumerate(lancamentos):
            if lanc[0] == lancamento_id:
                index_editado = i
                break
        
        if index_editado is not None:
            # Atualizar o lançamento específico
            c.execute('''
                UPDATE lancamentos 
                SET data = ?, historico = ?, complemento = ?, entrada = ?, saida = ?
                WHERE id = ?
            ''', (data, historico, complemento, entrada, saida, lancamento_id))
            
            # Recalcular todos os saldos a partir do lançamento editado
            for i in range(index_editado, len(lancamentos)):
                if i == index_editado:
                    # Para o lançamento editado, usar saldo anterior
                    if i == 0:
                        saldo = entrada - saida
                    else:
                        saldo_anterior = lancamentos[i-1][7]  # SALDO do lançamento anterior
                        saldo = saldo_anterior + entrada - saida
                else:
                    # Para lançamentos seguintes, recalcular baseado no anterior
                    entrada_atual = lancamentos[i][5] if i != index_editado else entrada
                    saida_atual = lancamentos[i][6] if i != index_editado else saida
                    saldo_anterior = lancamentos[i-1][7] if i > 0 else 0
                    saldo = saldo_anterior + entrada_atual - saida_atual
                
                # Atualizar saldo no banco
                lanc_id = lancamentos[i][0] if i != index_editado else lancamento_id
                c.execute('UPDATE lancamentos SET saldo = ? WHERE id = ?', (saldo, lanc_id))
            
            conn.commit()
            return True
        else:
            st.error("❌ Lançamento não encontrado")
            return False
            
    except Exception as e:
        st.error(f"❌ Erro ao atualizar lançamento: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def excluir_lancamento(lancamento_id, mes):
    """Exclui um lançamento específico"""
    conn = sqlite3.connect('livro_caixa.db', check_same_thread=False)
    c = conn.cursor()
    try:
        # Buscar o lançamento a ser excluído
        c.execute('SELECT * FROM lancamentos WHERE id = ?', (lancamento_id,))
        lancamento = c.fetchone()
        
        if lancamento:
            # Excluir o lançamento
            c.execute('DELETE FROM lancamentos WHERE id = ?', (lancamento_id,))
            
            # Recalcular saldos dos lançamentos seguintes
            c.execute('SELECT * FROM lancamentos WHERE mes = ? ORDER BY data, id', (mes,))
            lancamentos_restantes = c.fetchall()
            
            for i, lanc in enumerate(lancamentos_restantes):
                if i == 0:
                    saldo = lanc[5] - lanc[6]  # entrada - saida
                else:
                    saldo_anterior = lancamentos_restantes[i-1][7]
                    saldo = saldo_anterior + lanc[5] - lanc[6]
                
                c.execute('UPDATE lancamentos SET saldo = ? WHERE id = ?', (saldo, lanc[0]))
            
            conn.commit()
            return True
        else:
            st.error("❌ Lançamento não encontrado")
            return False
            
    except Exception as e:
        st.error(f"❌ Erro ao excluir lançamento: {e}")
        conn.rollback()
        return False
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
                # CORREÇÃO: usar ponto e vírgula como delimitador
                csv_data = df.to_csv(index=False, sep=';', encoding='utf-8-sig')
                zipf.writestr(nome_arquivo, csv_data)
        
        output.seek(0)
        return output
        
    except Exception as e:
        st.error(f"❌ Erro ao exportar dados: {e}")
        return None

# Função para download CSV individual por mês
def download_csv_mes(mes):
    """Gera CSV individual para um mês específico"""
    df_mes = get_lancamentos_mes(mes)
    if not df_mes.empty:
        # Selecionar colunas para exportação
        colunas_exportar = ['DATA', 'HISTORICO', 'COMPLEMENTO', 'ENTRADA', 'SAIDA', 'SALDO']
        colunas_existentes = [col for col in colunas_exportar if col in df_mes.columns]
        
        if colunas_existentes:
            df_export = df_mes[colunas_existentes].copy()
            
            # Renomear colunas
            mapeamento_colunas = {
                'DATA': 'Data',
                'HISTORICO': 'Histórico',
                'COMPLEMENTO': 'Complemento',
                'ENTRADA': 'Entrada_R$',
                'SAIDA': 'Saída_R$',
                'SALDO': 'Saldo_R$'
            }
            df_export.columns = [mapeamento_colunas[col] for col in colunas_existentes]
            
            # Formatar datas
            if 'Data' in df_export.columns:
                df_export['Data'] = pd.to_datetime(df_export['Data']).dt.strftime('%d/%m/%Y')
            
            # Converter para CSV com ponto e vírgula
            csv_data = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig')
            return csv_data
    return None

# Inicializar bancos de dados
init_db()
init_auth_db()

# Verificar se o usuário está logado
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

# Página de Login
if not st.session_state.logged_in:
    st.title("🔐 Login - Livro Caixa")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Usando markdown para exibir o emoji como texto
        st.markdown("""
        <div style="text-align: center; font-size: 80px; padding: 20px;">
            🔒
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        with st.form("login_form"):
            st.subheader("Acesso Restrito")
            username = st.text_input("Usuário", placeholder="Digite seu usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            submitted = st.form_submit_button("🚪 Entrar", use_container_width=True)
            
            if submitted:
                if username and password:
                    if login_user(username, password):
                        st.success(f"✅ Bem-vindo, {username}!")
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")
        
        st.markdown("---")
        
        # Criar novo usuário (apenas na página de login)
        with st.expander("👥 Criar Novo Usuário"):
            with st.form("create_user_form"):
                st.subheader("Novo Usuário")
                new_username = st.text_input("Novo Usuário", placeholder="Digite o nome de usuário")
                new_password = st.text_input("Nova Senha", type="password", placeholder="Digite a senha")
                confirm_password = st.text_input("Confirmar Senha", type="password", placeholder="Confirme a senha")
                
                create_submitted = st.form_submit_button("👤 Criar Usuário", use_container_width=True)
                
                if create_submitted:
                    if new_username and new_password and confirm_password:
                        if new_password == confirm_password:
                            if create_user(new_username, new_password):
                                st.success(f"✅ Usuário '{new_username}' criado com sucesso!")
                            else:
                                st.error("❌ Erro ao criar usuário. Nome de usuário já existe.")
                        else:
                            st.error("❌ As senhas não coincidem!")
                    else:
                        st.warning("⚠️ Preencha todos os campos!")
        
        #st.info("""
        #**Credenciais padrão:**
        #- **Usuário:** admin
        #- **Senha:** admin123
        #""")
    
    st.stop()

# Aplicação principal (apenas para usuários logados)
# Sidebar com logo e informações do usuário
with st.sidebar:
    # Tenta carregar a imagem do logo
    logo_carregado = carregar_imagem_logo("Logo_Loja.png")
    
    if not logo_carregado:
        st.sidebar.info("💡 Para usar seu logo, coloque o arquivo 'Logo_Loja.png' na mesma pasta do aplicativo")
    
    st.title("📒 Livro Caixa")
    
    # Informações do usuário logado
    st.sidebar.markdown("---")
    st.sidebar.success(f"👤 **Usuário:** {st.session_state.username}")
    
    # Botão de logout
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        logout_user()
        st.rerun()
    
    # Alterar senha
    with st.sidebar.expander("🔑 Alterar Senha"):
        with st.form("change_password_form"):
            new_password = st.text_input("Nova Senha", type="password")
            confirm_password = st.text_input("Confirmar Senha", type="password")
            
            if st.form_submit_button("💾 Alterar Senha"):
                if new_password and confirm_password:
                    if new_password == confirm_password:
                        change_password(st.session_state.username, new_password)
                        st.success("✅ Senha alterada com sucesso!")
                    else:
                        st.error("❌ As senhas não coincidem!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")
    
    # Gerenciar usuários (apenas para admin)
    if st.session_state.username == 'admin':
        with st.sidebar.expander("👥 Gerenciar Usuários"):
            st.subheader("Usuários do Sistema")
            
            # Listar usuários existentes
            users = get_all_users()
            if users:
                st.write("**Usuários cadastrados:**")
                for i, (username, created_at) in enumerate(users, 1):
                    st.write(f"{i}. **{username}** - Criado em: {created_at[:10]}")
                
                st.markdown("---")
                
                # Excluir usuário
                st.subheader("Excluir Usuário")
                user_to_delete = st.selectbox(
                    "Selecione o usuário para excluir:",
                    [user[0] for user in users if user[0] != 'admin']
                )
                
                if user_to_delete:
                    if st.button("🗑️ Excluir Usuário", use_container_width=True):
                        if st.checkbox("✅ Confirmar exclusão do usuário"):
                            success, message = delete_user(user_to_delete)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            else:
                st.info("Nenhum usuário cadastrado.")
    
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
        - ✅ **Acesso Protegido**: Sistema de login seguro
        - ✅ **Gerenciamento de Usuários**: Crie e gerencie múltiplos usuários
        - ✅ **Banco de Dados SQLite**: Dados salvos localmente
        - ✅ **Contas Personalizáveis**: Adicione suas próprias contas
        - ✅ **Edição de Lançamentos**: Edite ou exclua lançamentos existentes
        - ✅ **Relatórios**: Balanço financeiro com gráficos
        - ✅ **Exportação**: Backup dos dados em CSV
        
        **📝 Nota:** Não se esqueça do saldo inicial em janeiro!
        """)
        
        st.markdown("---")
        st.subheader("🎯 Como Usar:")
        
        st.markdown("""
        1. **📝 Contas**: Configure suas contas personalizadas
        2. **📥 Lançamentos**: Adicione entradas e saídas por mês
        3. **✏️ Editar**: Modifique ou exclua lançamentos existentes
        4. **📈 Balanço**: Veja relatórios e gráficos
        5. **💾 Exportar**: Faça backup dos dados
        """)
    
    with col2:
        st.subheader("💡 Dicas Importantes")
        
        st.markdown("""
        **💰 Movimentações:**
        - **Deposito em banco** → **Saída** do caixa
        - **Retirada do banco** → **Entrada** do caixa
        - **Pagamento** → **Saída** do caixa
        - **Recebimento** → **Entrada** do caixa
        
        **🔐 Segurança:**
        - Altere a senha padrão do admin
        - Crie usuários individuais para cada pessoa
        - Mantenha suas credenciais seguras
        - Faça logout ao terminar
        """)
        
        # Informações sobre gerenciamento de usuários
        if st.session_state.username == 'admin':
            st.subheader("👥 Admin")
            st.markdown("""
            **Privilégios de administrador:**
            - Criar novos usuários
            - Excluir usuários
            - Ver todos os usuários
            - Gerenciar todo o sistema
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
    
    # Exibir lançamentos do mês com opção de edição
    st.subheader(f"📋 Lançamentos - {mes_selecionado}")
    
    if not df_mes.empty:
        # Mapear colunas do banco para os nomes exibidos
        colunas_mapeadas = {
            'ID': 'ID',
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
            
            # Formatar colunas para exibição
            df_exibir_display = df_exibir.copy()
            if 'DATA' in df_exibir_display.columns:
                df_exibir_display['DATA'] = pd.to_datetime(df_exibir_display['DATA']).dt.strftime('%d/%m/%Y')
            if 'ENTRADA' in df_exibir_display.columns:
                df_exibir_display['ENTRADA'] = df_exibir_display['ENTRADA'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "")
            if 'SAÍDA' in df_exibir_display.columns:
                df_exibir_display['SAÍDA'] = df_exibir_display['SAÍDA'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "")
            if 'SALDO' in df_exibir_display.columns:
                df_exibir_display['SALDO'] = df_exibir_display['SALDO'].apply(lambda x: f"R$ {x:,.2f}")
            
            # Exibir tabela responsiva
            st.dataframe(df_exibir_display, use_container_width=True, hide_index=True)
            
            # Download CSV individual do mês
            st.subheader("📥 Download do Mês")
            csv_data = download_csv_mes(mes_selecionado)
            if csv_data:
                st.download_button(
                    label=f"💾 Baixar {mes_selecionado} em CSV",
                    data=csv_data,
                    file_name=f"livro_caixa_{mes_selecionado}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Seção de Edição de Lançamentos
            st.subheader("✏️ Gerenciar Lançamentos")
            
            # Selecionar lançamento para editar
            if 'ID' in df_exibir.columns:
                lancamentos_opcoes = []
                for idx, row in df_exibir.iterrows():
                    valor = row['ENTRADA'] if row['ENTRADA'] > 0 else row['SAÍDA']
                    descricao = f"{row['DATA']} - {row['HISTÓRICO']} - R$ {valor:,.2f}"
                    lancamentos_opcoes.append((row['ID'], descricao))
                
                if lancamentos_opcoes:
                    lancamento_selecionado = st.selectbox(
                        "**Selecione o lançamento para editar/excluir:**",
                        options=lancamentos_opcoes,
                        format_func=lambda x: x[1]
                    )
                    
                    if lancamento_selecionado:
                        lancamento_id = lancamento_selecionado[0]
                        lancamento_data = df_exibir[df_exibir['ID'] == lancamento_id].iloc[0]
                        
                        col_edit, col_del = st.columns([3, 1])
                        
                        with col_edit:
                            # Formulário de edição
                            with st.form("form_editar_lancamento"):
                                st.write("**Editar Lançamento:**")
                                col6, col7, col8 = st.columns([2, 2, 1])
                                
                                with col6:
                                    data_editar = st.date_input("**Data**", 
                                                              value=datetime.strptime(str(lancamento_data['DATA']), '%Y-%m-%d').date() 
                                                              if isinstance(lancamento_data['DATA'], str) 
                                                              else lancamento_data['DATA'].date())
                                    historico_editar = st.text_input("**Histórico**", value=lancamento_data['HISTÓRICO'])
                                
                                with col7:
                                    complemento_editar = st.text_input("**Complemento**", value=lancamento_data['COMPLEMENTO'] 
                                                                      if pd.notna(lancamento_data['COMPLEMENTO']) else "")
                                    
                                    # Determinar tipo de movimento baseado nos valores
                                    if lancamento_data['ENTRADA'] > 0:
                                        tipo_movimento_editar = "Entrada"
                                        entrada_editar = st.number_input("**Valor Entrada (R$)**", 
                                                                        value=float(lancamento_data['ENTRADA']), 
                                                                        min_value=0.0, step=0.01, format="%.2f")
                                        saida_editar = 0.0
                                    else:
                                        tipo_movimento_editar = "Saída"
                                        saida_editar = st.number_input("**Valor Saída (R$)**", 
                                                                      value=float(lancamento_data['SAÍDA']), 
                                                                      min_value=0.0, step=0.01, format="%.2f")
                                        entrada_editar = 0.0
                                
                                with col8:
                                    st.write("")  # Espaçamento
                                    st.write("")  # Espaçamento
                                    submitted_editar = st.form_submit_button("💾 Atualizar", use_container_width=True)
                                
                                if submitted_editar and historico_editar:
                                    # Atualizar lançamento no banco
                                    if atualizar_lancamento(lancamento_id, mes_selecionado, data_editar, historico_editar, 
                                                          complemento_editar, entrada_editar, saida_editar):
                                        st.success("✅ Lançamento atualizado com sucesso!")
                                        st.rerun()
                        
                        with col_del:
                            st.write("**Excluir:**")
                            if st.button("🗑️ Excluir", use_container_width=True, type="secondary"):
                                if st.checkbox("✅ Confirmar exclusão"):
                                    if excluir_lancamento(lancamento_id, mes_selecionado):
                                        st.success("✅ Lançamento excluído com sucesso!")
                                        st.rerun()
            
            # Estatísticas do mês
            st.subheader("📊 Estatísticas do Mês")
            
            col9, col10, col11 = st.columns(3)
            
            total_entradas = df_mes['ENTRADA'].sum() if 'ENTRADA' in df_mes.columns else 0.0
            total_saidas = df_mes['SAIDA'].sum() if 'SAIDA' in df_mes.columns else 0.0
            
            if 'SALDO' in df_mes.columns and len(df_mes) > 0:
                saldo_atual = df_mes.iloc[-1]['SALDO']
            else:
                saldo_atual = 0.0
            
            with col9:
                st.metric("💰 Total de Entradas", f"R$ {total_entradas:,.2f}")
            with col10:
                st.metric("💸 Total de Saídas", f"R$ {total_saidas:,.2f}")
            with col11:
                st.metric("🏦 Saldo Atual", f"R$ {saldo_atual:,.2f}")
        else:
            st.warning("⚠️ Estrutura de dados incompatível.")
            st.dataframe(df_mes, use_container_width=True)
    else:
        st.info(f"📭 Nenhum lançamento encontrado para {mes_selecionado}")
    
    # Botão para limpar lançamentos do mês
    if st.button(f"🗑️ Limpar TODOS os Lançamentos de {mes_selecionado}", use_container_width=True, type="secondary"):
        if st.checkbox("✅ Confirmar exclusão de TODOS os lançamentos"):
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
        
        # Download de CSV individual por mês
        st.subheader("📥 Download por Mês")
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        mes_download = st.selectbox("**Selecione o mês para download:**", meses)
        csv_data = download_csv_mes(mes_download)
        
        if csv_data:
            st.download_button(
                label=f"💾 Baixar {mes_download} em CSV",
                data=csv_data,
                file_name=f"livro_caixa_{mes_download}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning(f"📭 Nenhum dado encontrado para {mes_download}")
        
        st.markdown("---")
        
        # Exportação completa
        st.subheader("📦 Exportação Completa")
        if st.button("📦 Exportar Todos os Dados", use_container_width=True):
            with st.spinner("Gerando arquivo ZIP..."):
                output = exportar_para_csv()
                
                if output is not None:
                    st.download_button(
                        label="💾 Baixar Arquivo ZIP Completo",
                        data=output,
                        file_name=f"livro_caixa_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
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
        - **Segurança:** Acesso por login
        - **Usuários:** Múltiplos usuários suportados
        """)

# Rodapé
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        <strong>CONSTITUCIONALISTAS-929</strong> - Livro Caixa | 
        Desenvolvido por Silmar Tolotto | 
        Usuário: {username} | 
        {date}
    </div>
    """.format(username=st.session_state.username, date=datetime.now().strftime('%d/%m/%Y %H:%M')),
    unsafe_allow_html=True
)
